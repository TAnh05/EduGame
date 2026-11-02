"""Execute the actual final-test JavaScript renderer using a minimal DOM stub."""
import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path


class FinalTestFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is needed to execute JavaScript")
    def test_renderer_works_after_first_submitted_answer(self):
        page = (Path(__file__).resolve().parents[1] / "web" / "final_test.html")
        html = page.read_text(encoding="utf-8")
        match = re.search(r"<script>(.*?)</script>", html, flags=re.S)
        self.assertIsNotNone(match)
        js = match.group(1).split("(async () => {", 1)[0]
        node_test = r'''
const vm = require("node:vm");
const source = JSON.parse(process.argv[1]);
let rendered = "";
const els = {
  "#progress": {style: {}},
  "#main": {set innerHTML(v) {rendered = v;}, get innerHTML() {return rendered;}},
  "#error": {textContent: ""},
  "#action": {onclick: null}
};
const ctx = vm.createContext({
  document: {querySelector: x => els[x], querySelectorAll: () => []},
  sessionStorage: {getItem: () => null, setItem: () => {}},
  window: {location: {search: "?attempt_id=test_attempt"}},
  URLSearchParams, console,
});
vm.runInContext(source, ctx);
vm.runInContext(`game = {
  title: "Test",
  questions: [
    {id: "q1", before: "One ___", after: "", is_blank: true,
     options: [{idx: 0, text: "A"}, {idx: 1, text: "B"}]},
    {id: "q2", before: "Question two", after: "", is_blank: false,
     options: [{idx: 0, text: "Yes"}, {idx: 1, text: "No"}]}
  ],
  progress: {q1: {idx: 0, ok: true, correct_idx: 0, correct_text: "A"}}
}; index = 1; render();`, ctx);
if (!rendered.includes("Đã trả lời 1/2 câu") ||
    !rendered.includes("Câu 2 / 2") ||
    !rendered.includes("One ___")) {
  throw new Error("The answered-question history or current question did not render");
}
if (vm.runInContext('tabAttemptId()', ctx) !== 'test_attempt') {
  throw new Error('URL attempt ID was not prioritized');
}
'''
        proc = subprocess.run(
            ["node", "-e", node_test, json.dumps(js)],
            capture_output=True, text=True, timeout=10
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
