document.addEventListener("DOMContentLoaded", () => {
  const BACKEND_URL = "http://localhost:8000";
  const sections = ["#landing-page", "#start-screen", "#quiz-screen", "#notes-screen", "#summary-audio-screen"];

  const linkInput = document.getElementById("youtube-link");
  const numInput = document.getElementById("num-questions");
  const difficultyButtons = document.querySelectorAll(".diff-options .diff-btn");
  let selectedDifficulty = "easy";
  let timerSeconds = 50;
  let timerInterval;
  let questionsData = [];

  function showSection(selector) {
    sections.forEach(sec => document.querySelector(sec).classList.add("hidden"));
    document.querySelector(selector).classList.remove("hidden");
  }

  function showLoader(sectionSelector, show) {
    const loader = document.querySelector(`${sectionSelector} .loader-section`);
    if (loader) loader.classList.toggle("hidden", !show);
  }

  document.querySelectorAll(".back-btn").forEach(btn => {
    btn.addEventListener("click", () => showSection("#landing-page"));
  });

  difficultyButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      difficultyButtons.forEach(b => b.classList.remove("selected"));
      btn.classList.add("selected");
      selectedDifficulty = btn.dataset.level;
    });
  });

  document.getElementById("test-btn").addEventListener("click", () => {
    showSection("#start-screen");
  });

  document.getElementById("start-btn").addEventListener("click", async () => {
    const link = linkInput.value.trim();
    const num = parseInt(numInput.value);
    if (!link) return alert("Please enter a YouTube link");
    if (isNaN(num) || num < 5 || num > 20) return alert("Select between 5 and 20 questions");
    timerSeconds = 10 * num; // 10 seconds per question
   

    showLoader("#start-screen", true);
    try {
      const res = await fetch(`${BACKEND_URL}/mcq`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link, num, diff: selectedDifficulty })
      });
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      questionsData = data;
      renderQuiz(data);
      showSection("#quiz-screen");
      document.getElementById("quiz-form").style.display = "block";
      startTimer();
    } catch (e) {
      alert("❌ " + e.message);
    } finally {
      showLoader("#start-screen", false);
    }
  });

  function formatTime(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  function startTimer() {
    const timeDisplay = document.getElementById("time");
    timeDisplay.textContent = formatTime(timerSeconds);
    clearInterval(timerInterval);
    timerInterval = setInterval(() => {
      timerSeconds--;
      if (timerSeconds < 0) timerSeconds = 0;
      timeDisplay.textContent = formatTime(timerSeconds);
      if (timerSeconds <= 0) {
        clearInterval(timerInterval);
        autoSubmitTest();
      }
    }, 1000);
  }

  document.getElementById("quiz-form").addEventListener("submit", function (e) {
    e.preventDefault();
    clearInterval(timerInterval);
    autoSubmitTest();
  });

  function autoSubmitTest() {
    let score = 0;
    const total = questionsData.length;
    questionsData.forEach((mcq, index) => {
      const selected = document.querySelector(`input[name="q${index}"]:checked`);
      const isCorrect = selected && selected.value === mcq.answer;
      const feedback = document.createElement("div");
      feedback.textContent = isCorrect ? "✅ Correct" : `❌ Incorrect. Correct: ${mcq.answer}`;
      feedback.className = isCorrect ? "correct" : "incorrect";
      document.getElementsByClassName("quiz-box")[index].appendChild(feedback);
      if (isCorrect) score++;
    });
    document.getElementById("result").innerHTML = `🎯 Your Score: ${score} / ${total}`;
    document.getElementById("submit-btn").disabled = true;
    document.querySelectorAll("input[type=radio]").forEach(el => el.disabled = true);
    document.getElementById("timer").innerHTML = "⌛ Time's up or test submitted.";
    showChart(score, total - score);
  }

  document.getElementById("notes-btn").addEventListener("click", async () => {
    const link = linkInput.value.trim();
    if (!link) return alert("Please enter a YouTube link");

    showSection("#notes-screen");
    showLoader("#notes-screen", true);
    try {
      const res = await fetch(`${BACKEND_URL}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link })
      });
      if (!res.ok) throw new Error((await res.json()).error);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const dl = document.getElementById("download-notes-btn");
      dl.href = url;
      dl.download = "notes.pdf";
      dl.classList.remove("hidden");
    } catch (e) {
      alert("❌ " + e.message);
    } finally {
      showLoader("#notes-screen", false);
    }
  });

  document.getElementById("summary-btn").addEventListener("click", async () => {
    const link = linkInput.value.trim();
    if (!link) return alert("Please enter a YouTube link");

    showSection("#summary-audio-screen");
    showLoader("#summary-audio-screen", true);
    try {
      const res = await fetch(`${BACKEND_URL}/summary-audio`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ link })
      });
      if (!res.ok) throw new Error((await res.json()).error);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);

      const audio = document.getElementById("audio-player");
      audio.src = url;
      audio.style.display = "block";
      audio.play();

      const dl = document.getElementById("download-audio-btn");
      dl.href = url;
      dl.download = "summary_audio.mp3";
      dl.classList.remove("hidden");
    } catch (e) {
      alert("❌ " + e.message);
    } finally {
      showLoader("#summary-audio-screen", false);
    }
  });

  function renderQuiz(questions) {
    const container = document.getElementById("quiz-container");
    container.innerHTML = questions.map((q, i) => `
      <div class="quiz-box">
        <div class="question" data-answer="${q.answer}">${i + 1}: ${q.question}</div>
        ${q.options.map(o => `
          <div class="option">
            <label><input type="radio" name="q${i}" value="${o}"/> ${o}</label>
          </div>`).join("")}
      </div>`).join("");
  }

  function showChart(correct, incorrect) {
    new Chart(document.getElementById("scoreChart").getContext("2d"), {
      type: "doughnut",
      data: {
        labels: ["Correct", "Incorrect"],
        datasets: [{
          data: [correct, incorrect],
          backgroundColor: ["#10b981", "#ef4444"]
        }]
      },
      options: {
        plugins: {
          legend: {
            position: 'bottom'
          }
        }
      }
    });
  }
});
