// The instructions sent to Claude. They run on the server, so students can't change them.
export type Role = { company: string; role: string; location?: string; category?: string };

export function cvPrompt(r: Role, jd: string, cv: string) {
  return `You are an experienced recruiter for entry-level finance roles in the UK and Europe. Tailor the candidate's CV to the role below.

Rules:
- Use only facts that appear in the candidate's CV. Never invent employers, dates, grades, numbers, skills or achievements.
- Reorder sections and bullets, and rephrase them, so the experience most relevant to this role comes first.
- Use the job description's vocabulary only where it truthfully matches the candidate's experience.
- Start bullets with strong past-tense verbs and keep every number already in the CV.
- Keep it to one page: about 450 to 600 words.
- British English. Plain text only: section headings in capitals, bullets starting with "- ". No markdown, no tables.
- After the CV, write a line containing only ### and then up to 4 short bullets saying what you changed and why.

Role: ${roleLine(r)}
Job description:
"""${jdText(jd)}"""

Candidate's CV:
"""${cv.slice(0, 15000)}"""`;
}

export function letterPrompt(r: Role, jd: string, cv: string, letter: string, name: string) {
  return `Write a cover letter for an entry-level finance candidate applying to the role below.

Rules:
- Use only facts from the candidate's CV and existing cover letter. Never invent experience, grades, numbers or personal connections.
- Explain why this firm and this role using only what the job description says. Where a firm-specific fact would help but is not given, write a placeholder in square brackets, for example [a recent deal you followed].
- 250 to 350 words in four short paragraphs. British English. Confident and specific; avoid stock openings such as "I am writing to express my interest".
- If an existing cover letter is given, match its voice.
- Plain text only. Start with "Dear Hiring Team," unless the job description names a contact. End with "Kind regards," and then ${name ? '"' + name + '"' : "the candidate's name if it appears in the CV"}.
- After the letter, write a line containing only ### and then up to 3 short bullets listing the placeholders the candidate must fill in.

Role: ${roleLine(r)}
Job description:
"""${jdText(jd)}"""

Candidate's CV:
"""${cv.slice(0, 15000)}"""

Candidate's existing cover letter:
"""${(letter || 'None given.').slice(0, 8000)}"""`;
}

export function feedbackPrompt(question: string, guide: string, answer: string) {
  return `You are a senior investment banker running a first-round interview for an entry-level role in London. Give feedback on the candidate's answer.

Question: ${question}
What a strong answer covers: ${guide}
Candidate's answer:
"""${answer.slice(0, 6000)}"""

Reply in plain text, British English, under 180 words, in this order:
Score: X/10
What works: 2 short bullets starting with "- "
Improve: 2 or 3 short bullets starting with "- "
For technical questions, correct any factual error plainly.`;
}

const roleLine = (r: Role) => `${r.role} at ${r.company}${r.location ? ' (' + r.location + ')' : ''}, category: ${r.category || 'Investment Banking'}`;
const jdText = (jd: string) => (jd ? jd.slice(0, 12000) : 'Not provided. Tailor to a typical role of this kind.');
