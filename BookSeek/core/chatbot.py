"""
chatbot.py  [UI/챗봇: 팀원 C]
추천된 책을 소개하는 AI 사서 챗봇.
ANTHROPIC_API_KEY가 있으면 Claude를 쓰고, 없으면 내장 사서로 동작한다.
- introduce(): 추천 목록 소개
- answer(): 질문에 답변
"""

import os
import random
from typing import List, Dict, Any, Optional

from core.recommender import MOOD_LABELS_KO


SYSTEM_PROMPT = (
    "당신은 데스크톱 도서 추천 앱 안의 따뜻하고 박식한 사서입니다. "
    "독자에게 짧은 추천 도서 목록을 소개하며, 독자가 좋아한 장르와 분위기를 "
    "바탕으로 각 책이 왜 취향에 맞는지 간단히 설명합니다. 친근하고 간결하게: "
    "한 줄의 인사로 시작한 뒤, 책마다 2~3문장의 짧은 단락으로 소개하세요. "
    "주어지지 않은 줄거리를 지어내지 마세요. 글머리 기호 목록을 쓰지 말고 "
    "자연스러운 문장으로 쓰세요. 반드시 한국어로 답하세요."
)


class BookChatbot:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model
        self._client = None
        self._mode = "offline"
        self._init_client()

    def _init_client(self) -> None:
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            return
        try:
            import anthropic  # type: ignore
            self._client = anthropic.Anthropic(api_key=key)
            self._mode = "online"
        except Exception:
            self._client = None
            self._mode = "offline"

    @property
    def mode(self) -> str:
        return self._mode

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def introduce(
        self,
        recommendations: List[Dict[str, Any]],
        rated_books: List[Dict[str, Any]],
    ) -> str:
        if not recommendations:
            return ("아직 추천할 만한 책을 찾지 못했어요. 읽으신 책 몇 권에 "
                    "평점을 매겨주시면 취향을 파악해 추천해 드릴게요!")
        if self._mode == "online":
            try:
                return self._introduce_online(recommendations, rated_books)
            except Exception:
                # Network or API hiccup: fall back gracefully.
                return self._introduce_offline(recommendations, rated_books)
        return self._introduce_offline(recommendations, rated_books)

    def answer(
        self,
        question: str,
        recommendations: List[Dict[str, Any]],
        rated_books: List[Dict[str, Any]],
    ) -> str:
        if self._mode == "online":
            try:
                return self._answer_online(question, recommendations, rated_books)
            except Exception:
                return self._answer_offline(question, recommendations)
        return self._answer_offline(question, recommendations)

    # ------------------------------------------------------------------ #
    # Online (Claude) implementations
    # ------------------------------------------------------------------ #
    def _context_block(self, recommendations, rated_books) -> str:
        liked = sorted(rated_books, key=lambda b: b.get("user_score", 0),
                       reverse=True)[:5]
        liked_str = "; ".join(
            f"{b['title']} (사용자 평점 {b.get('user_score')}/10)" for b in liked
        ) or "아직 없음"

        rec_lines = []
        for r in recommendations:
            genres = ", ".join(r.get("genres", [])[:4]) or "미상"
            moods = ", ".join(r.get("moods", [])) or "미지정"
            match = r.get("match")
            match_str = f"{match}% 일치" if match is not None else "인기 도서"
            desc = (r.get("description") or "").strip().replace("\n", " ")
            if len(desc) > 280:
                desc = desc[:280] + "..."
            rec_lines.append(
                f"- {r['title']} / {r.get('author') or '작자 미상'} "
                f"[{match_str}; 장르: {genres}; 분위기: {moods}]"
                + (f" 줄거리: {desc}" if desc else "")
            )
        rec_str = "\n".join(rec_lines)
        return (f"독자가 좋아한 책: {liked_str}.\n\n"
                f"소개할 추천 도서:\n{rec_str}")

    def _introduce_online(self, recommendations, rated_books) -> str:
        context = self._context_block(recommendations, rated_books)
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=900,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    "이 추천 도서들을 소개해 주세요.\n\n" + context
                ),
            }],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()

    def _answer_online(self, question, recommendations, rated_books) -> str:
        context = self._context_block(recommendations, rated_books)
        msg = self._client.messages.create(
            model=self.model,
            max_tokens=700,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": (
                    f"현재 추천 상황입니다:\n\n{context}\n\n"
                    f"독자의 질문: {question}\n\n"
                    "주어진 정보만 사용해서 친절하게 답해주세요."
                ),
            }],
        )
        return "".join(
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ).strip()

    # ------------------------------------------------------------------ #
    # Offline template implementations
    # ------------------------------------------------------------------ #
    _OPENERS = [
        "마음에 드실 만한 책 몇 권을 골라봤어요.",
        "좋아하셨던 책들을 바탕으로, 시간을 들일 만한 책들을 추렸어요.",
        "당신의 취향에 맞춰 작은 추천 목록을 준비했어요.",
        "서가를 둘러보다 당신에게 어울릴 책들이 눈에 띄었어요.",
    ]

    def _introduce_offline(self, recommendations, rated_books) -> str:
        liked = sorted(rated_books, key=lambda b: b.get("user_score", 0),
                       reverse=True)
        parts = [random.choice(self._OPENERS)]

        if liked:
            top = liked[0]
            parts[0] += (f" “{top['title']}”에 {top.get('user_score')}/10점을 "
                         "주셨기에 그 방향으로 골라봤어요.")

        for i, r in enumerate(recommendations, start=1):
            author = r.get("author") or "작자 미상"
            sentence = f"\n\n{i}. “{r['title']}” / {author}."

            match = r.get("match")
            if match is not None:
                sentence += f" 당신의 취향과 약 {match:.0f}% 일치해요."

            reasons = r.get("reasons") or []
            if reasons:
                sentence += " " + reasons[0] + "."

            desc = (r.get("description") or "").strip()
            if desc:
                snippet = desc.split(". ")[0].strip()
                if len(snippet) > 200:
                    snippet = snippet[:200].rstrip() + "..."
                sentence += f" {snippet}"
            elif r.get("genres"):
                g = ", ".join(r["genres"][:3])
                sentence += f" {g} 계열의 주제를 담고 있어요."

            parts.append(sentence)

        parts.append("\n\n이 중에 더 알고 싶은 책이 있거나, 분위기로 좁혀드릴까요?")
        return "".join(parts)

    def _answer_offline(self, question, recommendations) -> str:
        q = question.lower().strip()

        # Try to match a specific recommended title mentioned in the question.
        for r in recommendations:
            title_words = r["title"].lower().split()
            if r["title"].lower() in q or (
                len(title_words) > 1
                and sum(w in q for w in title_words) >= max(2, len(title_words) // 2)
            ):
                return self._describe_book_offline(r)

        # Mood-based filtering, matching both English keys and Korean labels.
        mood_terms = {
            "dark": ["dark", "어두운", "어두"],
            "uplifting": ["uplifting", "밝은", "밝", "긍정"],
            "romantic": ["romantic", "로맨", "로맨틱", "사랑"],
            "adventurous": ["adventurous", "모험"],
            "reflective": ["reflective", "사색", "잔잔"],
            "mysterious": ["mysterious", "미스터리", "미스테리"],
            "whimsical": ["whimsical", "환상", "기발"],
            "tense": ["tense", "긴장", "스릴"],
            "epic": ["epic", "웅장", "대서사"],
            "cozy": ["cozy", "아늑", "편안", "따뜻"],
        }
        for mood, terms in mood_terms.items():
            if any(t in q for t in terms):
                matches = [r for r in recommendations
                           if mood in [m.lower() for m in r.get("moods", [])]]
                ko = MOOD_LABELS_KO.get(mood, mood)
                if matches:
                    titles = ", ".join(f"“{m['title']}”" for m in matches)
                    return (f"{ko} 분위기라면 {titles}을(를) 추천드려요. "
                            "그중 더 자세히 알려드릴까요?")
                return (f"지금 추천 목록엔 특별히 {ko} 분위기의 책은 없네요. "
                        f"{ko} 책 몇 권에 평점을 매겨주시면 다시 추천해 드릴게요.")

        if any(w in q for w in ["짧", "짧은", "분량", "페이지", "쪽", "short",
                                "quick", "page", "length"]):
            with_pages = [r for r in recommendations if r.get("page_count")]
            if with_pages:
                shortest = min(with_pages, key=lambda r: r["page_count"])
                return (f"이 중 가장 짧은 책은 “{shortest['title']}”로, "
                        f"약 {shortest['page_count']}쪽이에요.")

        # Generic fallback: re-list the top picks.
        titles = ", ".join(f"“{r['title']}”" for r in recommendations[:5])
        return ("추천 도서 중 무엇이든 더 알려드릴 수 있어요: "
                f"{titles}. 책 이름을 말씀해 주시거나, 분위기로 물어보셔도 돼요 "
                "(예: ‘밝은 분위기 있어?’).")

    @staticmethod
    def _describe_book_offline(r: Dict[str, Any]) -> str:
        author = r.get("author") or "작자 미상"
        head = f"“{r['title']}”은(는) {author}의 작품이에요"
        if r.get("publish_year"):
            head = (f"“{r['title']}”은(는) {author}의 작품으로, "
                    f"{r['publish_year']}년에 처음 출간되었어요")
        head += "."
        lines = [head]

        if r.get("genres"):
            lines.append(f"{', '.join(r['genres'][:4])} 계열의 책이에요.")
        if r.get("moods"):
            moods_ko = ", ".join(MOOD_LABELS_KO.get(m.lower(), m)
                                 for m in r["moods"])
            lines.append(f"전반적인 분위기는 {moods_ko}이에요.")
        desc = (r.get("description") or "").strip()
        if desc:
            if len(desc) > 400:
                desc = desc[:400].rstrip() + "..."
            lines.append(desc)
        if r.get("match") is not None:
            lines.append(f"전체적으로 당신의 취향과 약 {r['match']:.0f}% 일치해요.")
        return " ".join(lines)
