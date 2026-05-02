import unittest
from unittest.mock import patch

from agents import chat_assistant


class ChatAssistantTests(unittest.TestCase):
    def test_classify_accepts_list_payload(self):
        with patch.object(chat_assistant.llm, "can_call", return_value=True), \
             patch.object(chat_assistant.llm, "ask_json", return_value=[{
                 "intent": "news_report",
                 "query": "latest AI news",
                 "limit": 3,
             }]):
            decision = chat_assistant._classify("write a report on latest AI news")

        self.assertEqual(decision["intent"], "news_report")
        self.assertEqual(decision["query"], "latest AI news")
        self.assertEqual(decision["limit"], 3)

    def test_classify_falls_back_on_bad_payload(self):
        with patch.object(chat_assistant.llm, "can_call", return_value=True), \
             patch.object(chat_assistant.llm, "ask_json", return_value=["bad"]):
            decision = chat_assistant._classify("write a report on latest news")

        self.assertEqual(decision["intent"], "news_report")

    def test_run_chat_once_reports_internal_error(self):
        sent = []
        with patch.object(chat_assistant, "_pending_messages", return_value=["status"]), \
             patch.object(chat_assistant, "_classify", side_effect=RuntimeError("boom")), \
             patch.object(chat_assistant.db, "append_chat_history") as append, \
             patch.object(chat_assistant.telegram, "send_message", side_effect=sent.append):
            chat_assistant.run_chat_once()

        self.assertIn("internal chat error", sent[0])
        append.assert_called_once()

    def test_news_report_intent_for_write_latest_news(self):
        decision = chat_assistant._heuristic_intent(
            "write a report on the latest news about US refunding India for the tariffs"
        )

        self.assertEqual(decision["intent"], "news_report")


if __name__ == "__main__":
    unittest.main()
