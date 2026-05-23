Work in /Users/mustafa/Downloads/sunnah.

Goal: Add Turkish translations to all missing "turkish" fields in collections/*.json.

Translate yourself. Do not use third-party translators. Use both "arabic" and any available English/context fields to understand the meaning. Preserve the JSON structure exactly. Add "turkish" only where it is missing or empty. Do not overwrite existing Turkish translations unless I explicitly ask for a style correction.

Before every batch, reread:
- /Users/mustafa/Downloads/sunnah/turkish-translation-glossary.md
- /Users/mustafa/Downloads/sunnah/translation-progress.json

Follow the glossary strictly. Use natural Turkish hadith style, especially narrator openings like:
- "Ebû Hüreyre'den rivayet edildiğine göre..."
- "Ebû Hüreyre'nin rivayet ettiğine göre..."
- "Hz. Âişe'den nakledildiğine göre..."

Avoid literal English/Arabic phrasing when Turkish has a better hadith style. For example, use "Öyle bir zaman gelecek ki..." instead of "Öyle bir zaman yaklaşır ki...".

Work batch by batch, starting from translation-progress.json. After every batch:
1. save the JSON file
2. validate JSON syntax
3. update translation-progress.json
4. keep exactly one progress block per collection file; update that collection's existing block from the original start reference through the newest completed reference instead of adding a new block for each batch
5. use compact cumulative ranges for contiguous translated references; keep "count" as the number translated in the batch just completed. For example, after a 20-item batch completes bukhari references 31 through 50, the single Bukhari block should be:
   {
     "file": "collections/bukhari.json",
     "translated_reference_range": "bukhari:1-50",
     "count": 20,
     "next_missing_reference": "bukhari:51"
   }
6. do not keep separate progress blocks such as "bukhari:1-10", "bukhari:11-30", and "bukhari:31-50"; merge them into the one cumulative block for collections/bukhari.json
7. update turkish-translation-glossary.md if a new recurring term/style decision appears
8. report which references were translated and what the next missing reference is

Keep chat context light. Do not carry completed hadith translations in memory after each batch. Treat the files on disk as the source of truth. For every new batch, reread translation-progress.json, turkish-translation-glossary.md, and only the next untranslated hadith entries from the JSON file.

Continue production translation from translation-progress.json until every missing Turkish field in all collections/*.json is filled.

Do not stop after a few batches. Keep working batch by batch until the last collection is complete, unless you hit a real blocker. Before every batch, reread turkish-translation-glossary.md and translation-progress.json. After every batch, save, validate JSON, update translation-progress.json by modifying the single cumulative block for that collection, update the glossary for recurring decisions, and continue to the next missing reference.

Only report concise progress checkpoints periodically. Final answer only when all collections are complete or a blocker requires my decision.
if you not sure about right turkish mean for a term , search similar turkish hadiths on  internet see how to use
