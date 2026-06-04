import json
import streamlit.components.v1 as components


def speak_question(question, question_number):
    safe_text = json.dumps(question)
    components.html(
        f"""
        <style>
          #play-question-{question_number} {{
            border:1px solid #d0d7de;
            border-radius:6px;
            padding:8px 12px;
            background:#ffffff;
            color:#0f172a;
            cursor:pointer;
            font:14px system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
            transition: background 0.18s ease, border-color 0.18s ease, color 0.18s ease;
          }}
          #play-question-{question_number}:hover,
          #play-question-{question_number}:focus {{
            background:#e0f2fe;
            border-color:#7dd3fc;
            color:#0f172a;
          }}
          #play-question-{question_number}:focus {{
            outline: 2px solid rgba(14, 165, 233, 0.6);
            outline-offset: 2px;
          }}
        </style>
        <div style="display:flex; gap:8px; align-items:center;">
          <button id="play-question-{question_number}">
            Play question audio
          </button>
          <span style="font:13px system-ui, -apple-system, BlinkMacSystemFont, sans-serif; color:#57606a;">
            Uses your browser's speech engine
          </span>
        </div>
        <script>
          const text = {safe_text};
          const button = document.getElementById("play-question-{question_number}");
          function speak() {{
            window.speechSynthesis.cancel();
            const utterance = new SpeechSynthesisUtterance(text);
            utterance.rate = 0.92;
            utterance.pitch = 1;
            window.speechSynthesis.speak(utterance);
          }}
          button.addEventListener("click", speak);
        </script>
        """,
        height=48,
    )
