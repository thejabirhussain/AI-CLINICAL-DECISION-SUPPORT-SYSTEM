# Knowledge Base Ingestion Scripts

Use these commands to populate your CDSS with authoritative clinical guidelines.
Run them from the `ai/` directory within your virtual environment.

> [!TIP]
> Each script runs idempotently. You can re-run them safely to pick up new content without duplicating vectors.

## Clinical Guidelines (General)

### 1. NICE Guidelines (UK)
```bash
python -m app.scripts.ingest_web --seed "https://www.nice.org.uk/guidance/published" --max-pages 200 --include-seed --allow-pdf
```

### 2. WHO Clinical Guidelines
```bash
python -m app.scripts.ingest_web --seed "https://www.who.int/publications/i/item/" --max-pages 300 --include-seed --allow-pdf --ignore-robots
```

### 3. CDC Diseases & Conditions
```bash
python -m app.scripts.ingest_web --seed "https://www.cdc.gov/diseasesconditions/" --max-pages 500 --allow-prefix "/diseasesconditions/"
```

### 4. Cochrane Library Summaries
```bash
python -m app.scripts.ingest_web --seed "https://www.cochranelibrary.com/cdsr/reviews" --max-pages 200 --ignore-robots
```

### 5. AAFP (American Academy of Family Physicians)
```bash
python -m app.scripts.ingest_web --seed "https://www.aafp.org/pubs/afp.html" --max-pages 150
```

## Internal Medicine

### 6. NCBI Bookshelf (High Quality Textbooks)
```bash
python -m app.scripts.ingest_web --seed "https://www.ncbi.nlm.nih.gov/books/" --max-pages 500 --allow-prefix "/books/NBK"
```

### 7. Merck Manual (Professional)
```bash
python -m app.scripts.ingest_web --seed "https://www.merckmanuals.com/professional" --max-pages 300
```

### 8. Medscape Reference (Drugs & Diseases)
```bash
python -m app.scripts.ingest_web --seed "https://emedicine.medscape.com/" --max-pages 200
```

## Cardiology

### 9. ESC Guidelines (European Society of Cardiology)
```bash
python -m app.scripts.ingest_web --seed "https://www.escardio.org/Guidelines" --max-pages 100 --allow-pdf
```

### 10. AHA Guidelines (American Heart Association)
```bash
python -m app.scripts.ingest_web --seed "https://professional.heart.org/en/science-news" --max-pages 100
```

## Oncology

### 11. NCCN Guidelines (National Comprehensive Cancer Network)
*Note: May require auth headers, this scrapes public summaries*
```bash
python -m app.scripts.ingest_web --seed "https://www.nccn.org/guidelines/category_1" --max-pages 100
```

### 12. ASCO Guidelines
```bash
python -m app.scripts.ingest_web --seed "https://www.asco.org/practice-patients/guidelines" --max-pages 100
```

## Pediatrics

### 13. AAP Gateway (Pediatrics)
```bash
python -m app.scripts.ingest_web --seed "https://publications.aap.org/pediatrics" --max-pages 150
```

## Pharmacology & Drug Safety

### 14. FDA Drug Safety Communications
```bash
python -m app.scripts.ingest_web --seed "https://www.fda.gov/drugs/drug-safety-and-availability" --max-pages 200
```

### 15. EMA (European Medicines Agency)
```bash
python -m app.scripts.ingest_web --seed "https://www.ema.europa.eu/en/human-medicines" --max-pages 200
```

### 16. DailyMed (NIH)
```bash
python -m app.scripts.ingest_web --seed "https://dailymed.nlm.nih.gov/dailymed/" --max-pages 300
```

## Emergency Medicine

### 17. ACEP Clinical Policies
```bash
python -m app.scripts.ingest_web --seed "https://www.acep.org/patient-care/clinical-policies" --max-pages 100
```

## Infectious Diseases

### 18. IDSA Guidelines
```bash
python -m app.scripts.ingest_web --seed "https://www.idsociety.org/practice-guideline/practice-guidelines" --max-pages 100
```

## Mental Health

### 19. APA Guidelines (Psychiatry)
```bash
python -m app.scripts.ingest_web --seed "https://psychiatryonline.org/guidelines" --max-pages 100
```

## Neurology

### 20. AAN Guidelines (Neurology)
```bash
python -m app.scripts.ingest_web --seed "https://www.aan.com/Guidelines/" --max-pages 100
```
