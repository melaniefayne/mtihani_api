CREATE_EXAM_PROMPT_TEXT = """
You are an expert Integrated Science teacher preparing exam questions for Junior Secondary School learners in Kenya (Grades 7–9, ages 11–14) for the topic "{sub_strand}" under the strand "{strand}".
Your goal is to create exam questions that are clear, relatable, and promote both conceptual understanding and higher-order thinking.

The questions should be based on the following learning outcomes:
{learning_outcomes}

The questions should also assess the following skills:
{skills_to_assess}

Each question must relate meaningfully to at least one of the above learning outcomes and one of the assessed skills.

You will receive a list of **skills to test**. For each skill, you must generate **EXACTLY ONE question-answer pair** that tests the given skill. You must generate exactly {question_count} pairs, matching the number of skills provided.
Note: Some skills may appear more than once in the list. Treat each repetition as a separate prompt — generate a **distinct** and **non-redundant** question-answer pair for each occurrence.

**Question Format Guidelines:**
- Each question may contain multiple sentences (e.g., a scenario followed by a prompt), but it must be phrased as a short paragraph that fits on one line — no line breaks, bullet points, or numbered lists.
- For **lower-order skills** (i.e., Remembering, Understanding, Evaluating): Use short, direct questions like “What is…”, “List two…”, “State…”.
- For **higher-order skills** (i.e., Applying, Analysing):
    - Begin each question with a **short, varied real-life scenario** that clearly reflects the sub_strand concept (e.g., classroom experiments, school gardens, home or market settings).
    - Follow the scenario with a prompt that encourages explanation, evaluation, justification, or problem-solving.
    - You may use longer sentences for such questions, but keep them clear, grammatically correct, and age-appropriate.
- For repeated skills, vary the real-life setting (e.g., classroom, home, farm, market, lab) and character names to avoid overlap in phrasing or examples.

**Stylistic Expectations:**
- Use Kenyan contexts and names but vary them across questions.
- Vary characters, situations, and sentence structures across the batch, even though the topic is the same.
- Integrate cross-disciplinary logic (biology, chemistry, physics) **only if clearly relevant to the sub_strand**.

**Important Constraints:**
- DO NOT use diagrams or suggest visual elements.
- DO NOT test for multiple skills in a single question.
- DO NOT skip any skill.
- Each question and each answer must be **on a single line**, complete, concise, and logically sound.

Use this structure per skill:
{{
  "question": "[your generated question here]",
  "expected_answer": "[concise but accurate answer here]"
}}

Here is the list of skills to test:
{skills_to_test}

Return ONLY the valid JSON array with `question` and `expected_answer` fields. No explanation, no markdown, and no commentary.
"""


MOCK_EXAM_ANSWERS_PROMPT_TEXT = """
would answer science exam questions under exam conditions.

Each student has an `avg_score`, representing their general performance and ability to understand, reason, and express scientific ideas. Use this to tailor the **depth**, **clarity**, **accuracy**, and **style** of each student's response.

---

**Scoring Guidance (based on avg_score):**

- **Below 50% – Very Limited Understanding**  
  Responses may be short, confused, off-topic, or show major misconceptions. Language may be disjointed or imprecise.

- **50–59% – Basic Understanding**  
  Responses are partially correct but vague or simplistic. Minor errors are common. Student may struggle with vocabulary or logic.

- **60–74% – Moderate Understanding**  
  Responses are mostly correct with some explanation. There may be shallow reasoning, missing links, or small inaccuracies.

- **75–84% – Good Understanding**  
  Responses are clear, mostly accurate, and show logical thinking. Language is appropriate for a Kenyan student in this age group.

- **85% and above – Excellent Understanding**  
  Responses are confident, well-structured, detailed, and precise. Student shows strong reasoning and age-appropriate scientific vocabulary.

---

**Important Simulation Guidelines:**

- **Answers must vary clearly based on avg_score** — reflect the student’s ability in vocabulary, phrasing, explanation quality, and logic.
- For **lower-scoring students**, it's okay to:
  - Use simple or broken grammar.
  - Show confusion, uncertainty, or factual errors.
  - Skip steps in reasoning or use general terms.
- For **higher-scoring students**, aim for:
  - Clear, articulate phrasing.
  - Full and accurate explanations with some technical terms (suitable for a 13-year-old Kenyan learner).
- **Do not reuse or lightly paraphrase** answers across students — each response must feel unique and consistent with the student's score.
- Responses should feel like **real Kenyan students writing in a school test**, not like polished textbook entries or AI responses.

---

**Your task:**
You will receive:
- A list of exam questions (`id`, `question`, `expected_answer`) – use `expected_answer` only for correctness reference.
- A list of students (`id`, `avg_score`).

Simulate how **each student** would realistically answer **each question**.

Return ONLY a valid JSON array (no explanation, no markdown)
**Return Format (strictly):**
A valid **JSON array**. Each item in the array must have the structure:
```json
{{
  "id": [student_id],
  "answers": [
    {{
      "question_id": "[question_id]",
      "answer": "[simulated student answer based on avg_score]"
    }},
    ...
  ]
}}

Here is the exam:
{exam}

And here's the list of students:
{student_list}

"""


GRADE_ANSWERS_PROMPT_TEXT = """
You are an expert Integrated Science teacher grading student responses for a Junior Secondary School exam in Kenya (Grades 7–9).

The question is:
{question}

The expected answer is:
{expected_answer}

These are the rubric levels for the key skill(s) assessed. Use them to evaluate how well each student responded:
{rubrics}

Each student answer has an `answer_id`. For each one:
- Evaluate how well it addresses the question.
- Match it to the most appropriate rubric level.
- Assign a score based on the rubric:
  - 1 = Below
  - 2 = Approaches
  - 3 = Meets
  - 4 = Exceeds

Return only a valid JSON array. Each object must include:
- "answer_id": the ID of the student's answer
- "score": the numeric rubric score (1–4)

Here are the student answers to grade:
{student_answers}

Your output:
[{{"answer_id": <int>, "score": <int>}}, ...]
No markdown, no extra explanation — just a clean JSON array.
"""

CLASSROOM_EXAM_INSIGHTS_PROMPT = """
You are an educational advisor analyzing classroom exam results. Below are the summary statistics for the class:
- average_score: The mean score of all students on the exam (percentage).
- average_expectation_level: The expectation category most students fall into (such as “Below”, “Approaching”, “Meets”, or “Exceeds”).
- score_distribution: A breakdown of the range or spread of scores (e.g., min, max, standard deviation, quartiles, or a frequency count per band).
- expectation_level_distribution: The percentage of students in each expectation level (e.g., “Exceeds: 20%, Meets: 50%, Approaching: 25%, Below: 5%”).
- bloom_skill_scores: The performance for each bloom skill tested

Your task:
- Generate a concise set of general insights describing overall class performance, strengths, weaknesses, and possible areas of concern or pride, using the information provided.
- Where helpful, highlight score gaps, celebrate strengths, and note any patterns in how students are distributed across expectation levels.

**Return Format (strictly):**
A valid **JSON array** of insights like so:

```json
[ ... insights ]
```

Now, provide general classroom performance insights for the following data:
{class_performance_data}
"""


STRAND_PERFORMANCE_INSIGHTS_PROMPT = """
You are an education advisor helping a science teacher analyze exam performance data. For each strand, you are given a detailed summary, including:
- The strand name and grade
- The average score and expectation level
- The bloom skill scores for the strand
- The score variance, with least and max scores and the standard deviation
- Sub-strand scores, showing which sub-strands are above or below the strand average
- Lists of top and bottom performing students for that strand

Your task:
- Carefully review the data for each strand
- For each strand, generate:
- a list of insights (in clear, detailed, teacher-friendly language) describing student performance patterns, struggles, and strengths. Use specific examples or scenarios where possible.
- a list of practical suggestions for how a teacher can address weaknesses, leverage strengths, or support struggling students, based on the data.
- Where possible, reference actual sub-strand names, expectation levels, and score differences in your explanations.

**Return Format (strictly):**
A valid **JSON array**. Each item in the array must have the structure:

```json
{{
  "strand": "<Strand Name>",
  "insights": [... your insighst here],
  "suggestions": [... your suggestions here]
}}

Now, using the format above, generate insights and suggestions for the following strand data:
{strand_performance_data}
"""


FLAGGED_SUB_STRAND_INSIGHTS_PROMPT = """
You are an educational assessment advisor helping a science teacher interpret student performance data.
Below, you have a list of sub-strand pairs (topics), each with a correlation value representing how student performance in the two sub-strands is related.
- A strong negative correlation (e.g., -0.6) means that students who do well in one topic tend to do poorly in the other.
- A strong positive correlation (e.g., +0.6) means students tend to do similarly well (or poorly) in both topics.

Your task:
For each sub-strand pair, write:
- a brief, clear insight (1–2 sentences) explaining what this correlation means for student learning (in plain, teacher-friendly language, mentioning both sub-strand names).
Where possible, give a concrete example scenario involving these two sub-strands, e.g., “If a student masters ‘Sub-strand A’ but struggles in ‘Sub-strand B’, or vice versa, this pattern may appear.”
- a brief, practical suggestion (1–2 sentences) for what the teacher can do to address this pattern (e.g., strategies, interventions, or follow-up activities).

**Return Format (strictly):**
A valid **JSON array**. Each item in the array must have the structure:
```json
{{
  "pair": ["Sub-strand A", "Sub-strand B"],
  "correlation": -0.65,
  "insight": "<your brief insight with a specific example>",
  "suggestion": "<your brief suggestion>"
}}

Now, using the format above, generate insights and suggestions for the following sub_strand data:
{sub_strand_correlations}
"""

CREATE_CLUSTER_FOLLOW_UP_QUIZ_PROMPT = """
You are an expert Integrated Science teacher creating targeted follow-up quizzes for a Junior Secondary School student group in Kenya (Grades 7–9, ages 11–14).

The students were tested in the exam with the following list of questions:
{exam_questions}

Below is a summary of this group's performance in this exam:
{cluster_performance}

Your Task:
Generate {question_count} new, original quiz questions that will help this group of students:
- Focus only on their weakest strands and skills
- Match their current level of understanding (scaffolded, not too hard or too easy)
- Use real-life contexts relevant to their grade
- Avoid repeating previous exam questions
- For each question, include a the grade, strand, sub-strand and the bloom skill it addresses. Also indicate the expected answer for each question

**Return Format (strictly):**
A valid **JSON array**. Each item in the array must have the structure:
```json
{{
  "question": "... your generated question here",
  "expected_answer": "... concise but accurate answer here"
  "grade": "... the grade the questions tests as a simple integer"
  "strand": "... the strand the questions tests"
  "sub_strand": "... the sub strand the questions tests"
  "bloom_skill": "... the bloom skill the questions tests"
}}

"""


EXTRACT_SUB_STRAND_CONTEXT_PROMPT= """
You are an expert Integrated Science teacher for Junior Secondary in Kenya (Grades 7–9).
Your task is to extract ONLY those questions that are *directly, specifically, and primarily* about the topic "{sub_strand}" under the strand "{strand}" from the provided document.
- Do NOT include questions that are about other topics or only generally related.
- Exclude questions that primarily address other sub-strands, even if they mention this one in passing.
- If you are not certain a question is about this sub-strand, leave it out.

Here is the topic description:
{description}

Here is the full text resource to extract from:
{reference_text}

Use this structure per skill:
{{
  "question": "[the extracted or created question here]",
  "expected_answer": "[concise but accurate answer here]"
}}

Return ONLY the valid JSON array with `question` and `expected_answer` fields. No explanation, no markdown, and no commentary.
"""
