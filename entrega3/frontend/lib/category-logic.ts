// frontend/src/lib/category-logic.ts

// 1. HARDCODED DATA (Canonical)
const CATEGORY_DATA: Record<string, string[]> = {
  therapeutic_category: [
    "Analgesics", "Anesthetics", "Antiarrhythmics", "Antibiotics", 
    "Anticonvulsants", "Antidepressants", "Antiemetics", "Antifungals", 
    "Antihistamines", "Antihypertensives", "Antipsychotics", "Antipyretics", 
    "Antivirals", "Anxiolytics", "Bronchodilators", "Corticosteroids", 
    "Diuretics", "Insulin", "NSAIDs", "PPIs", "Vaccines", "Vitamins"
  ],
  route: [
    "AURICULAR (OTIC)", "BUCCAL", "CONJUNCTIVAL", "CUTANEOUS", "DENTAL", 
    "EPIDURAL", "EXTRACORPOREAL", "INFILTRATION", "INTRA-ARTERIAL", 
    "INTRA-ARTICULAR", "INTRABRONCHIAL", "INTRACANALICULAR", "INTRACAUDAL", 
    "INTRADERMAL", "INTRALESIONAL", "INTRAMENINGEAL", "INTRAMUSCULAR", 
    "INTRAOCULAR", "INTRAPLEURAL", "INTRASYNOVIAL", "INTRATHECAL", 
    "INTRAVASCULAR", "INTRAVENOUS", "INTRAVENTRICULAR", "INTRAVITREAL", 
    "NASAL", "OPHTHALMIC", "ORAL", "OROPHARYNGEAL", "PARENTERAL", 
    "PERCUTANEOUS", "PERINEURAL", "PERIODONTAL", "RECTAL", 
    "RESPIRATORY (INHALATION)", "RETROBULBAR", "SOFT TISSUE", "SUBARACHNOID", 
    "SUBCONJUNCTIVAL", "SUBCUTANEOUS", "SUBLINGUAL", "SUBMUCOSAL", 
    "SUPRACHOROIDAL", "TOPICAL", "TRANSDERMAL", "TRANSMUCOSAL", 
    "TRANSTRACHEAL", "VAGINAL"
  ],
  product_type: [
    "CELLULAR THERAPY", "HUMAN OTC DRUG", "HUMAN PRESCRIPTION DRUG"
  ]
}

// 2. MANUAL SYNONYMS
const CUSTOM_ALIASES: Record<string, string[]> = {
  // --- PRODUCT TYPES ---
  "HUMAN OTC DRUG": ["otc", "shelf", "over the counter", "generic", "generical"],
  "HUMAN PRESCRIPTION DRUG": ["prescription", "prescribed", "rx", "script"],

  // --- THERAPEUTIC CATEGORIES ---
  "Analgesics": ["pain", "ache", "aching"],
  "Anesthetics": ["numb"], 
  "Antibiotics": ["bacterial", "infection"], 
  "Antidepressants": ["depression", "depressant"],
  "Antiemetics": ["nausea", "vomiting", "motion sickness", "motion sick"],
  "Antifungals": ["fungus", "fungal", "yeast"], 
  "Antihistamines": ["allergy", "sneezing", "hay fever", "allergies"],
  "Antihypertensives": ["blood pressure", "hypertension", "bp", "hyper tension"],
  "Antipsychotics": ["psychosis", "bipolar", "schizophrenia"],
  "Antipyretics": ["fever", "temperature"],
  "Antivirals": ["virus", "viral", "flu", "herpes"], 
  "Anxiolytics": ["anxiety", "panic", "calm", "relaxant"],
  "Bronchodilators": ["asthma", "wheezing", "breath"], 
  "Corticosteroids": ["steroid", "inflammation", "cortisone"],
  "Diuretics": ["fluid", "bloating", "retention"], 
  "Insulin": ["diabetes", "diabetic", "blood sugar"],
  "NSAIDs": ["swelling"],
  "PPIs": ["acid", "reflux", "heartburn", "gerd", "ulcer"],
  "Vaccines": ["shot", "immunization", "booster", "vax"],
  "Vitamins": ["supplement", "mineral", "multivitamin"],

  // --- ROUTES ---
  "ORAL": ["mouth", "pill", "tablet", "capsule", "syrup", "liquid", "swallow", "chewable", "lozenge"],
  "TOPICAL": ["cream", "gel", "ointment", "lotion", "balm", "rub"],
  "TRANSDERMAL": ["patch"],
  "OPHTHALMIC": ["eye"],
  "AURICULAR (OTIC)": ["ear"],
  "NASAL": ["nose", "spray", "nostril"],
  "RESPIRATORY (INHALATION)": ["inhaler", "nebulizer", "lung", "breathe"],
  "INTRAVENOUS": ["iv", "drip", "vein"],
  "INTRAMUSCULAR": ["im", "muscle", "injection"],
  "SUBCUTANEOUS": ["subq", "sc"],
  "SUBLINGUAL": ["under tongue"],
  "RECTAL": ["suppository", "enema"],
  "DENTAL": ["tooth", "gum","teeth"],
  "VAGINAL": ["douche"],
}

// 3. TYPES - UPDATED
export interface ActiveFilter {
  field: string
  value: string
  displayValue: string 
  matchedAlias: string // <--- NEW FIELD: Stores "im", "pain", etc.
}

// 4. BUILD LOOKUP MAP 
const LOOKUP_MAP: Record<string, { field: string, value: string }> = {}

const addToMap = (key: string, field: string, value: string) => {
  if (key && key.length > 1) { 
    LOOKUP_MAP[key.toLowerCase()] = { field, value }
  }
}

Object.entries(CATEGORY_DATA).forEach(([field, values]) => {
  values.forEach((canonicalVal) => {
    addToMap(canonicalVal, field, canonicalVal)
    if (canonicalVal.endsWith('s') && !canonicalVal.endsWith('ss')) {
      addToMap(canonicalVal.slice(0, -1), field, canonicalVal)
    }
    if (canonicalVal.includes('(')) {
      const parts = canonicalVal.split(/[\(\)]/).map(s => s.trim()).filter(Boolean)
      parts.forEach(part => addToMap(part, field, canonicalVal))
    }
    if (canonicalVal.includes(' ')) {
      const words = canonicalVal.split(' ')
      words.forEach(word => addToMap(word, field, canonicalVal))
    }
    if (CUSTOM_ALIASES[canonicalVal]) {
      CUSTOM_ALIASES[canonicalVal].forEach(alias => {
        addToMap(alias, field, canonicalVal)
      })
    }
  })
})

const SORTED_KEYS = Object.keys(LOOKUP_MAP).sort((a, b) => b.length - a.length)

// 5. EXTRACTION LOGIC - UPDATED
export function extractFilterFromQuery(
  query: string, 
  ignoredAliases: string[] = [] // Check against ALIASES now
): { 
  cleanQuery: string, 
  foundFilter: ActiveFilter | null 
} {
  const tempQuery = query.toLowerCase()
  
  for (const key of SORTED_KEYS) {
    const regex = new RegExp(`\\b${key}\\b`, 'i')
    
    if (regex.test(tempQuery)) {
      const match = LOOKUP_MAP[key]

      // CHECK: If the *alias* (the key) is in the ignore list, skip it.
      if (ignoredAliases.includes(key)) {
        continue
      }
      
      const foundFilter: ActiveFilter = {
        field: match.field,
        value: match.value,
        displayValue: `${match.field}: ${match.value}`,
        matchedAlias: key // <--- Save the alias ("im")
      }

      const newQuery = query.replace(regex, '').replace(/\s{2,}/g, ' ').trim()

      return { cleanQuery: newQuery, foundFilter }
    }
  }

  return { cleanQuery: query, foundFilter: null }
}