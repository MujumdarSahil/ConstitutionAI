<template>
  <div class="quiz-question" :class="`type-${question.question_type}`">
    <!-- Question number and type -->
    <div class="question-meta">
      <span class="question-number">Q{{ index + 1 }}</span>
      <span class="question-type-badge">{{ typelabel }}</span>
    </div>

    <!-- Question text -->
    <div class="question-text">{{ question.question }}</div>

    <!-- MCQ Options -->
    <div v-if="question.question_type === 'mcq'" class="options-grid" role="radiogroup">
      <label
        v-for="(option, i) in question.options"
        :key="i"
        class="option-label"
        :class="{
          'selected': selectedAnswer === option,
          'correct': showResult && option === question.correct_answer,
          'wrong': showResult && selectedAnswer === option && option !== question.correct_answer,
          'disabled': submitted || showResult,
        }"
      >
        <input
          type="radio"
          :name="`q-${question._id}`"
          :value="option"
          v-model="selectedAnswer"
          :disabled="submitted || showResult"
          class="sr-only"
        />
        <span class="option-letter">{{ 'ABCD'[i] }}</span>
        <span class="option-text">{{ option }}</span>
        <span v-if="showResult && option === question.correct_answer" class="option-icon">✓</span>
        <span v-else-if="showResult && selectedAnswer === option && option !== question.correct_answer" class="option-icon">✗</span>
      </label>
    </div>

    <!-- Match the Following -->
    <div v-else-if="question.question_type === 'match'" class="options-grid" role="radiogroup">
      <label
        v-for="(option, i) in question.options"
        :key="i"
        class="option-label"
        :class="{
          'selected': selectedAnswer === option,
          'correct': showResult && option === question.correct_answer,
          'wrong': showResult && selectedAnswer === option && option !== question.correct_answer,
          'disabled': submitted || showResult,
        }"
      >
        <input
          type="radio"
          :name="`q-${question._id}`"
          :value="option"
          v-model="selectedAnswer"
          :disabled="submitted || showResult"
          class="sr-only"
        />
        <span class="option-letter">{{ 'ABCD'[i] }}</span>
        <span class="option-text match-text">{{ option }}</span>
        <span v-if="showResult && option === question.correct_answer" class="option-icon">✓</span>
      </label>
    </div>

    <!-- Short Answer -->
    <div v-else-if="question.question_type === 'short_answer'" class="short-answer-area">
      <textarea
        v-model="selectedAnswer"
        :disabled="submitted || showResult"
        placeholder="Write your answer here in 3–4 sentences..."
        class="short-answer-input"
        rows="5"
        :id="`short-answer-${question._id}`"
      ></textarea>
      <div class="short-answer-hint">
        Tip: Include key constitutional concepts, case references, and article connections.
      </div>
    </div>

    <!-- Submit button -->
    <div v-if="!showResult" class="question-footer">
      <button
        class="btn btn-primary"
        :disabled="!selectedAnswer || submitted"
        @click="$emit('submit', { questionId: question._id, answer: selectedAnswer })"
        :id="`submit-q-${index}`"
      >
        {{ submitted ? 'Submitted...' : 'Submit Answer' }}
      </button>
    </div>

    <!-- Result section -->
    <div v-if="showResult" class="result-section" :class="result?.is_correct ? 'result-correct' : 'result-wrong'">
      <div class="result-header">
        <span class="result-icon">{{ result?.is_correct ? '✅' : '❌' }}</span>
        <span class="result-label">{{ result?.is_correct ? 'Correct!' : 'Incorrect' }}</span>
        <ScoreBadge :score="result?.score || 0" size="sm" />
      </div>
      <div v-if="!result?.is_correct" class="correct-answer">
        <strong>Correct Answer:</strong> {{ question.correct_answer }}
      </div>
      <div class="result-explanation">
        <strong>Explanation:</strong> {{ result?.ai_explanation || question.explanation }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ScoreBadge from './ScoreBadge.vue'

const props = defineProps({
  question: { type: Object, required: true },
  index:    { type: Number, default: 0 },
  showResult: { type: Boolean, default: false },
  result:   { type: Object, default: null },
})

const emit = defineEmits(['submit'])
const selectedAnswer = ref('')
const submitted = ref(false)

const typelabel = {
  mcq:          'Multiple Choice',
  match:        'Match the Following',
  short_answer: 'Short Answer',
}[props.question.question_type] || 'Question'
</script>

<style scoped>
.quiz-question {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-xl);
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
  animation: fadeIn 0.3s ease;
}

.question-meta {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.question-number {
  font-family: var(--font-mono);
  font-size: 0.8rem;
  font-weight: 700;
  color: var(--color-accent);
  background: var(--color-accent-dim);
  border: 1px solid var(--color-accent);
  padding: 0.2em 0.6em;
  border-radius: var(--radius-full);
}

.question-type-badge {
  font-size: 0.7rem;
  font-weight: 600;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.question-text {
  font-size: 1.05rem;
  font-weight: 600;
  color: var(--color-text-primary);
  line-height: 1.5;
}

/* MCQ / Match options */
.options-grid {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

.option-label {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all var(--transition-fast);
  position: relative;
}

.option-label:hover:not(.disabled) {
  border-color: var(--color-accent);
  background: var(--color-accent-dim);
}

.option-label.selected {
  border-color: var(--color-accent);
  background: var(--color-accent-dim);
}

.option-label.correct {
  border-color: var(--color-success);
  background: var(--color-success-dim);
}

.option-label.wrong {
  border-color: var(--color-danger);
  background: var(--color-danger-dim);
}

.option-label.disabled {
  cursor: default;
}

.option-letter {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-weight: 700;
  font-size: 0.8rem;
  background: var(--color-bg-elevated);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.option-text {
  flex: 1;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}

.match-text {
  font-family: var(--font-mono);
  font-size: 0.85rem;
}

.option-icon {
  font-weight: 700;
  font-size: 1.1rem;
}

/* Short answer */
.short-answer-area {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.short-answer-input {
  min-height: 130px;
  font-size: 0.95rem;
  line-height: 1.6;
}

.short-answer-hint {
  font-size: 0.78rem;
  color: var(--color-text-muted);
  font-style: italic;
}

/* Footer */
.question-footer {
  display: flex;
  justify-content: flex-end;
}

/* Result section */
.result-section {
  border-radius: var(--radius-lg);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  font-size: 0.9rem;
  line-height: 1.6;
  animation: fadeIn 0.4s ease;
}

.result-correct {
  background: var(--color-success-dim);
  border: 1px solid var(--color-success);
}
.result-wrong {
  background: var(--color-danger-dim);
  border: 1px solid var(--color-danger);
}

.result-header {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  font-weight: 700;
}

.result-icon { font-size: 1.2rem; }
.result-label { font-size: 1rem; color: var(--color-text-primary); }

.correct-answer {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.result-explanation {
  color: var(--color-text-secondary);
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-3);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  border: 0;
}
</style>
