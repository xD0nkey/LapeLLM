# Script generation workflow

This workflow helps AI agents generate conservative Lape scripts without relying on guessed APIs or unsupported patterns.

1. Identify the script task clearly before writing code.
2. Identify the likely relevant domains, such as inventory, banking, walking, minimap, GUI, OCR, color matching, mouse input, client state, antiban, or base script structure.
3. Check the local repository documentation first, starting with the relevant topic file under docs/.
4. Check SRL-T documentation when base-library behavior, Simba-facing helpers, or SRL-T symbols may be involved.
5. Check WaspLib documentation when WaspLib wrappers, base script behavior, walker logic, finders, or WaspLib-specific symbols may be involved.
6. Check existing local examples if they are available and relevant.
7. Separate confirmed facts from assumptions and keep the distinction explicit.
8. Generate only conservative code that matches documented patterns.
9. Ask for a working example when the required syntax or API is not confirmed.
10. Update the known gaps document when repeated uncertainty blocks reliable script generation.
