# Multi-Agent Debate System

Two AI debaters argue any topic from opposite sides, and an impartial AI judge declares the winner.

Built with **LangGraph** (LangChain). Debaters and moderator run on **GPT-4o-mini**, the judge on **GPT-4o**, through OpenAI or Azure OpenAI.

## How it works

1. **Moderator** turns your topic into a debatable motion and flips a coin for speaking order.
2. **Debaters** give opening statements, rebuttal rounds, and closing statements. Each one sees its own speeches as its turns and the opponent's as the other side of the conversation.
3. **Judge** scores both sides on argument strength, evidence and logic, rebuttal effectiveness, and clarity, then picks a winner. Safeguards:
   - It judges twice with the A/B labels swapped. If the runs disagree, the combined scores decide.
   - Every decisive moment must quote the transcript, and each quote is checked in code.
   - Vague appeals such as "studies show" are detected in code and must be listed as unsupported claims. Citations are treated as unverified.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
copy .env.example .env
```

In `.env`, set an endpoint and key for each model. For Azure OpenAI, paste the deployment URL: the deployment name and `api-version` are read from it. Leave an endpoint empty to use api.openai.com.

## Run

```powershell
.\.venv\Scripts\python main.py "Remote work is better than office work" --rounds 2
```

| Option | Default | Meaning |
|---|---|---|
| `--rounds` | 2 | Rebuttal rounds |
| `--word-limit` | 250 | Words per speech |
| `--single-judge` | off | Skip the label-swapped second judge run |
| `--seed` | random | Seed for the speaking-order coin flip |
| `--out` | `transcripts/` | Where Markdown and JSON transcripts are saved |

## Examples

### Commands

```powershell
# Default: 2 rebuttal rounds, judged twice with the A/B labels swapped
.\.venv\Scripts\python main.py "Social media does more harm than good for teenagers"

# Shorter and cheaper: 1 rebuttal round, a single judge run
.\.venv\Scripts\python main.py "Remote work is better than office work" --rounds 1 --single-judge

# Reproducible speaking order and longer speeches
.\.venv\Scripts\python main.py "Cities should ban private cars from downtown areas" --seed 42 --word-limit 350
```

### Example debate

A real run with `--rounds 1`: GPT-4o-mini debaters and GPT-4o judge on Azure OpenAI. The model output below is unedited.

**Motion:** This house believes that social media does more harm than good for teenagers.

- **FOR:** The side in favor of the motion must argue that social media negatively impacts teenagers' mental health, self-esteem, and social skills, leading to harmful consequences such as anxiety and depression.
- **AGAINST:** The side against the motion must argue that social media provides valuable opportunities for connection, self-expression, and access to information, which can enhance teenagers' social lives and well-being.

The coin flip made AGAINST speak first, so the speaking order was: AGAINST opening, FOR opening, AGAINST rebuttal, FOR rebuttal, AGAINST closing, FOR closing.

#### Verdict: AGAINST wins, 28.5 to 26.5

| Criterion | FOR | AGAINST |
|---|---:|---:|
| Argument strength | 7.5 | 7.5 |
| Evidence and logic | 5.0 | 6.5 |
| Rebuttal effectiveness | 6.5 | 6.5 |
| Clarity persuasion | 7.5 | 8.0 |
| **Total** | **26.5** | **28.5** |

Scores are averaged over the two judge runs.

**How it was decided.** Both judge runs picked whichever debater was labelled "B": AGAINST in run 1 (AGAINST 30, FOR 25) and FOR in run 2 (FOR 28, AGAINST 27). The label swap exposed that letter bias, so the combined scores decided: AGAINST 57, FOR 53.

**Why FOR lost on evidence.** The vague-evidence detector flagged two of FOR's sentences ("Studies reveal…", "The evidence shows…"). Both judge runs listed them as unsupported claims and capped FOR's evidence score at 5.

**Judge's rationale**

> _Debater A argued FOR; Debater B argued AGAINST._
>
> Debater A presented a strong case for the harms of social media, particularly regarding mental health and self-esteem. However, their reliance on unsupported claims and failure to address some of Debater B's points weakened their position. Debater B effectively reframed the debate by focusing on the potential for positive outcomes with proper usage and provided a more balanced perspective. While both sides had dropped arguments, Debater B's overall case was more compelling and better supported.

**Decisive moments** (every quote was checked against the transcript and found)

- Debater A (FOR): Opening statement: "Studies reveal that excessive use correlates with heightened levels of anxiety and depression in teenagers." This moment establishes a key argument for the motion, linking social media use to mental health issues. However, the claim is vague and unsupported, which weakens its impact.
- Debater B (AGAINST): Rebuttal 1: "Rather than blaming social media, we should focus on promoting healthy usage and digital literacy among teenagers." This counters Debater A's argument by reframing the issue as one of usage rather than inherent harm, shifting the focus to solutions rather than condemnation.
- Debater A (FOR): Rebuttal 1: "The very nature of social media fosters comparison, and for many, this leads to detrimental impacts that are hard to escape." This reinforces the argument about social media's inherent design flaws, directly addressing Debater B's point about healthy usage by arguing that the platforms themselves are problematic.
- Debater B (AGAINST): Closing statement: "By embracing social media's positive potential and equipping teenagers with the skills to navigate it wisely, we can enhance their lives rather than harm them." This encapsulates Debater B's stance, emphasizing the potential for positive outcomes with proper guidance, and counters the idea that social media is inherently harmful.

**Issues flagged**

- FOR, unsupported claim: "Studies reveal that excessive use correlates with heightened levels of anxiety and depression in teenagers."
- FOR, unsupported claim: "The evidence shows that these harmful effects far outweigh any potential support networks online."
- FOR, dropped argument: Debater B's point about social media serving as a bridge for shy individuals was not directly addressed.
- AGAINST, dropped argument: Debater A's point about the culture of validation creating fragile self-esteem was not fully addressed.

<details>
<summary><strong>Full transcript (6 speeches)</strong></summary>

#### AGAINST: Opening statement

Ladies and gentlemen, today we are tasked with a crucial discussion about the role of social media in the lives of teenagers. I stand firmly against the motion that social media does more harm than good for this demographic. In fact, social media serves as a powerful tool for connection, self-expression, and access to vital information, all of which enhance teenagers' social lives and well-being.

First, social media facilitates meaningful connections among peers. In a world where geographical boundaries can limit friendships, platforms like Instagram and Snapchat allow teenagers to maintain relationships, share experiences, and find communities that resonate with their interests. This connectivity fosters a sense of belonging, which is essential for healthy emotional development.

Second, social media is a vibrant space for self-expression. Platforms like TikTok and YouTube empower teenagers to share their creativity, showcase their talents, and voice their opinions. This not only builds confidence but also cultivates important skills such as communication and digital literacy, which are crucial in today’s job market.

Finally, social media is an invaluable resource for information and support. Whether it’s accessing educational content, mental health resources, or social justice initiatives, teenagers can utilize these platforms to become informed and engaged citizens.

While there are challenges associated with social media, the benefits it offers far outweigh the negatives. It is a dynamic tool that, when used thoughtfully, can significantly contribute to the well-being and growth of teenagers. Thank you.

#### FOR: Opening statement

Ladies and gentlemen, today we stand in favor of the motion that social media does more harm than good for teenagers. While my opponent highlights the connectivity and self-expression afforded by social media, we must scrutinize the deeper, more damaging implications these platforms have on mental health, self-esteem, and social skills among adolescents.

First, social media significantly impacts mental health. Studies reveal that excessive use correlates with heightened levels of anxiety and depression in teenagers. The constant exposure to curated lives can lead to unrealistic comparisons, fostering feelings of inadequacy and loneliness. Instead of genuine connections, teens often find themselves in a virtual environment that amplifies their insecurities.

Second, social media undermines self-esteem. Platforms that prioritize likes and shares create a culture of validation that translates self-worth into online approval. Many teenagers suffer when they don’t receive the attention they crave, which can trigger a downward spiral of self-doubt and emotional distress.

Lastly, social media diminishes real-life social skills. Face-to-face interactions are crucial for developing emotional intelligence and empathy, yet teenagers increasingly rely on digital communication. This reliance stunts their ability to navigate complex social situations, leading to difficulties in forming lasting relationships.

In conclusion, while my opponent lauds the benefits of social media, we must recognize that the harm it inflicts on mental health, self-esteem, and interpersonal skills far outweighs any potential advantages. Thank you.

#### AGAINST: Rebuttal 1

Thank you. My opponent raises valid concerns regarding mental health and self-esteem, but their arguments overlook the broader context and potential of social media as a tool for growth and resilience.

First, while it is true that excessive use of social media can correlate with mental health issues, it’s essential to recognize that these problems often stem from underlying factors rather than the platforms themselves. Rather than blaming social media, we should focus on promoting healthy usage and digital literacy among teenagers. Social media can be a space for support and camaraderie, where teens share their struggles and find understanding, significantly counteracting feelings of isolation.

Regarding self-esteem, my opponent suggests that social media fosters a validation culture reliant on likes and shares. However, this perspective disregards the empowerment many teenagers feel when they engage authentically. Numerous teenagers leverage social media to celebrate their unique identities, find communities that align with their values, and uplift each other. The focus should be on teaching teens to cultivate self-worth independent of online metrics, rather than condemning the platforms altogether.

Lastly, while my opponent argues that social media diminishes real-life social skills, it can actually complement in-person interactions. Digital platforms often serve as a bridge, encouraging shy or introverted teens to connect and build confidence before transitioning to face-to-face communication.

In summary, rather than viewing social media solely as a harmful influence, we should embrace its potential for connection, growth, and community-building in teenagers’ lives. Thank you.

#### FOR: Rebuttal 1

Thank you. While my opponent raises valid points about the potential of social media, they underestimate the pervasive harm it inflicts on teenagers.

Firstly, claiming that mental health issues stem from underlying factors rather than social media disregards the undeniable evidence linking screen time to increased anxiety and depression. Even if some teens find support online, this does not negate the fact that the pressure to maintain an online image can exacerbate feelings of isolation and inadequacy. The very nature of social media fosters comparison, and for many, this leads to detrimental impacts that are hard to escape.

Moreover, while my opponent argues that social media can be a platform for empowerment and authentic self-expression, we must acknowledge that this experience is often overshadowed by the prevailing culture of validation through likes and shares. Many teenagers feel that their worth is contingent upon social media approval, leading to anxiety and a fragile sense of self-esteem. The focus should not just be on empowerment but on understanding the psychological toll that constant validation can take.

Lastly, my opponent suggests that social media can enhance real-life interactions, yet it often creates a false sense of connection. Many teens become so accustomed to digital communication that they struggle in face-to-face settings, leading to a decrease in essential social skills. Ultimately, while there may be some positive aspects, they do not outweigh the significant risks that social media poses to teenagers' mental health and social development. Thank you.

#### AGAINST: Closing statement

Ladies and gentlemen, as we conclude this debate, it’s essential to recap the key points of contention and why our position against the motion is stronger.

First, on the issue of mental health, my opponent argues that social media exacerbates anxiety and depression. However, we emphasized the importance of addressing underlying factors and promoting healthy usage. Social media can be a supportive space that enhances wellness, not just a platform for comparison.

Second, concerning self-esteem, my opponent highlights the culture of validation through likes. Yet, we demonstrated that social media can also empower self-expression and foster communities that uplift teenagers. It is crucial to focus on teaching resilience and self-worth beyond social media metrics rather than condemning the platforms outright.

Finally, regarding social skills, my opponent suggests that digital communication hinders interpersonal abilities. In contrast, we argued that social media can serve as a bridge for shy individuals, ultimately facilitating real-life interactions rather than diminishing them.

In summary, while there are challenges associated with social media, the opportunities it provides for connection, self-expression, and support far outweigh the negatives. By embracing social media's positive potential and equipping teenagers with the skills to navigate it wisely, we can enhance their lives rather than harm them. Therefore, I urge you to vote against the motion. Thank you.

#### FOR: Closing statement

Ladies and gentlemen, as we conclude this debate, let’s revisit the key clashes that underline why we firmly support the motion that social media does more harm than good for teenagers.

First, on mental health, my opponent suggests that social media can be a supportive space. However, we demonstrated that the very design of these platforms fosters constant comparison and magnifies feelings of inadequacy, leading to anxiety and depression among teens. The evidence shows that these harmful effects far outweigh any potential support networks online.

Second, concerning self-esteem, while my opponent argues social media empowers teens, we highlighted that the culture of validation through likes creates a fragile sense of self-worth. Many teenagers find their self-esteem directly tied to online approval, which can lead to devastating emotional consequences.

Lastly, on social skills, my opponent claims that social media enhances interpersonal abilities. In reality, we illustrated that reliance on digital communication often hinders face-to-face interactions, leaving many teens ill-equipped to navigate real-world social dynamics.

In summary, the risks associated with social media—damaging mental health, undermining self-esteem, and impairing social skills—are far too significant to overlook. While my opponent acknowledges the challenges, they fail to adequately address the overwhelming evidence of harm. Therefore, we urge you to vote in favor of the motion, recognizing the need for a more critical view of social media's impact on teenagers. Thank you.

</details>

## Tests

```powershell
.\.venv\Scripts\python -m pytest
```

The tests use fake models and make no API calls.

## Layout

```
main.py             CLI entry point
debate/
  config.py         Per-model endpoints and keys, debate settings
  graph.py          LangGraph wiring: frame motion, speaking loop, judge
  agents.py         Agent factories, message builders, judge reconciliation, quote and evidence checks
  prompts.py        Moderator, debater and judge prompts
  schemas.py        Structured outputs (motion, scorecard, verdict)
  state.py          Graph state
  render.py         Terminal output and transcript export
tests/
```

## Known limitations

- The vague-evidence detector matches common phrasings, not every one.
- The judge cannot verify citations; debaters are steered toward reasoning instead.
- The word limit is enforced by the prompt, so speeches can run slightly over.
