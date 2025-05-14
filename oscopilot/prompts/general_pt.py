extraction_prompts = {
    "GAIA_DIRECTIVE_ANSWER_PICKER": '''
    You are operating as a dedicated response summarizer. Given a task prompt and its associated content, your role is to isolate the required answer precisely, based on embedded instructions.

    Your behavior must follow these protocols:
    1. If the prompt is quantitative, retrieve only the number(s) mentioned in the response.
    2. If qualitative, mimic the format shown in the guidance examples.
    3. Apply any transformation rules indicated within the question before finalizing the output.
    4. Match the structure and format outlined explicitly in the question itself.

    Below are representative samples to guide your extractions:

    Q: I'm recovering from illness and missed Friday’s lecture. My classmate sent me an audio file where the professor discussed topics for the Calculus midterm. I need to know the reading pages. The file is named Homework.mp3. Please list the page numbers in increasing order, comma-separated.
    A: Pages included in the Homework.mp3 file (already sorted) were: 132, 133, 134, 197, 245.  
    Final: 132, 133, 134, 197, 245

    Q: How many participants actually enrolled in the NIH trial on H. pylori and acne between Jan and May 2018?
    A: NIH listing under 'Study Design' shows a total of 90 enrolled individuals.  
    Final: 90

    Q: Where are the Vietnamese insect samples from Kuznetzov’s 2010 publication stored, as per Nedoshivina’s paper? Provide just the city name in full.
    A: The specimens were archived at the Zoological Institute, in the city of Saint Petersburg.  
    Final: Saint Petersburg

    Q: Who has the player numbers directly before and after Taish Tamai’s as of July 2023? Format as: LastnameBefore, LastnameAfter (Roman characters only).
    A: Tamai wears number 19. Surrounding him: 18 - Yamasaki, 20 - Uehara.  
    Final: Yamasaki, Uehara

    Q: Decode the sentence hidden in this 5x7 block, reading left-to-right:
                THESE
                AGULL
                GLIDE
                DPEAC
                EFULL
                YTOMY
                CHAIR
    A: If we read by columns across all rows, we get: "The seagull glided peacefully to my chair."  
    Final: The seagull glided peacefully to my chair.

    Q: Evaluate these logical identities. Which one is inconsistent with the others?
       ¬(A ∧ B) ↔ (¬A ∨ ¬B), ¬(A ∨ B) ↔ (¬A ∧ ¬B), (A → B) ↔ (¬B → ¬A),
       (A → B) ↔ (¬A ∨ B), (¬A → B) ↔ (A ∨ ¬B), ¬(A → B) ↔ (A ∧ ¬B)
    A: All except this are standard equivalences: (¬A → B) ↔ (A ∨ ¬B) is incorrect.  
    Final: (¬A → B) ↔ (A ∨ ¬B)

    Now perform the extraction for the following case using the instructions above. Your response must contain only the final extracted answer, without explanation.

    Prompt: {question}
    Content: {response}
    Output:
    '''
}
