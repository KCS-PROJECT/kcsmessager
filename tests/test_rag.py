# -*- coding: utf-8 -*-
"""RagService 테스트 - 색인/권한 필터/문서 파싱/추출형 답변 (LLM 비활성)"""

import os
import shutil
import tempfile
import unittest

os.environ['KCS_RAG_LLM'] = 'off'

from server.kakao.rag import RagService, extract_terms, chunk_text, decode_document  # noqa: E402


def msg(msg_id, room_id, sender, content, kind='text'):
    return {'msg_id': msg_id, 'room_id': room_id, 'sender': sender, 'kind': kind,
            'content': content, 'timestamp': '2026-10-08T10:00:00', 'deleted': False}


class RagTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.rag = RagService(os.path.join(self.dir, 'rag.db'))

    def tearDown(self):
        self.rag.close()
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_extract_terms_strips_particles(self):
        self.assertEqual(extract_terms('주간회의는 언제 어디에서 해?'), ['주간회의'])
        self.assertIn('회의실', extract_terms('회의실을 알려줘'))
        self.assertIn('예산', extract_terms('예산이 얼마야'))

    def test_chunking(self):
        text = '\n\n'.join(f'문단 {i} ' + '가' * 180 for i in range(6))
        chunks = chunk_text(text)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(c) <= 700 for c in chunks))
        self.assertEqual(chunk_text('   '), [])

    def test_room_permission_filter(self):
        self.rag.index_message(msg(1, 'r1', '김철수', '이번 분기 마케팅 예산은 3천만원입니다'))
        self.rag.index_message(msg(2, 'secret', '최지우', '비밀 프로젝트 예산은 9억입니다'))
        hits = self.rag.search('예산 얼마야', '홍길동', ['r1'])
        self.assertEqual([h['source_id'] for h in hits], [1])
        hits = self.rag.search('예산 얼마야', '최지우', ['r1', 'secret'])
        self.assertEqual(sorted(h['source_id'] for h in hits), [1, 2])

    def test_index_skips_non_text_and_duplicates(self):
        self.rag.index_message(msg(1, 'r1', 'a', '사진', kind='image'))
        self.rag.index_message(msg(2, 'r1', 'a', '배송 일정 확인 부탁'))
        self.rag.index_message(msg(2, 'r1', 'a', '배송 일정 확인 부탁'))
        self.assertEqual(len(self.rag.search('배송 일정', 'a', ['r1'])), 1)
        self.rag.remove_message(2)
        self.assertEqual(self.rag.search('배송 일정', 'a', ['r1']), [])

    def test_documents_owner_scope_and_delete(self):
        doc = self.rag.add_document('홍길동', '휴가규정.md', '# 휴가 규정\n\n연차는 입사 1년 후 15일이 부여됩니다.'.encode('utf-8'))
        self.assertEqual(doc['chunks'], 1)
        self.assertEqual(self.rag.search('연차 며칠', '홍길동', [])[0]['title'], '휴가규정.md')
        self.assertEqual(self.rag.search('연차 며칠', '김철수', []), [])
        self.assertEqual([d['name'] for d in self.rag.list_documents('홍길동')], ['휴가규정.md'])
        self.assertFalse(self.rag.delete_document(doc['doc_id'], '김철수'))
        self.assertTrue(self.rag.delete_document(doc['doc_id'], '홍길동'))
        self.assertEqual(self.rag.search('연차', '홍길동', []), [])

    def test_decode_document_formats(self):
        self.assertIn('안녕', decode_document('a.txt', '안녕하세요'.encode('cp949')))
        with self.assertRaises(ValueError):
            decode_document('a.exe', b'MZ')
        with self.assertRaises(ValueError):
            decode_document('a.txt', b'   ')

    def test_extractive_answer_cites_sources(self):
        self.rag.add_document('홍길동', '출장규정.txt', '국내 출장 일비는 하루 5만원이며 숙박비는 실비로 정산한다.'.encode())
        answer = self.rag.answer('출장 일비 얼마?', '홍길동', [], [])
        self.assertIn('5만원', answer)
        self.assertIn("문서 '출장규정.txt'", answer)
        self.assertIn('찾지 못했어요', self.rag.answer('양자역학', '홍길동', [], []))

    def test_question_not_cited_as_source(self):
        self.rag.index_message(msg(1, 'r1', '이영희', '@AI 비서 이번 주 물류 일정 요약해줘'))
        self.rag.index_message(msg(2, 'bot', '홍길동', '물류 일정 알려줘'))
        self.rag.index_message(msg(3, 'r1', '김철수', '이번 주 물류 일정은 수요일 입고, 금요일 출고입니다'))
        answer = self.rag.answer('물류 일정 알려줘', '홍길동', ['r1', 'bot'], [])
        self.assertIn('수요일 입고', answer)
        self.assertNotIn('요약해줘', answer)
        self.assertEqual(answer.count('[1]'), 2)  # 본문 1회 + 출처 1회 → 근거 1개뿐

    def test_persistence(self):
        self.rag.index_message(msg(1, 'r1', 'a', '서버 점검은 토요일 새벽 2시'))
        again = RagService(os.path.join(self.dir, 'rag.db'))
        self.assertEqual(len(again.search('서버 점검', 'a', ['r1'])), 1)
        again.close()


if __name__ == '__main__':
    unittest.main()
