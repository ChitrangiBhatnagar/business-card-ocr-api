# SalesCentri Integration Guide

## Quick Integration for salescentri.com

### 1. Deploy the OCR API

```bash
# Push to your repo (connected to Render)
git add .
git commit -m "Add business card OCR with enrichment"
git push origin main
```

On Render.com Dashboard:
1. Go to your service settings
2. Add Environment Variable:
   - `GOOGLE_API_KEY` = `your-google-api-key-here` (get from https://console.cloud.google.com/apis/credentials)
3. Deploy

Your API URL: `https://business-card-ocr-api.onrender.com`

---

### 2. Add to SalesCentri Next.js

#### Install dependency:
```bash
npm install react-dropzone
```

#### Add environment variable to `.env.local`:
```
NEXT_PUBLIC_OCR_API_URL=https://business-card-ocr-api.onrender.com
```

#### Copy the component:
Copy `BusinessCardScanner.tsx` to your components folder.

#### Use in a page:
```tsx
// app/dashboard/business-cards/page.tsx
import BusinessCardScanner from "@/components/BusinessCardScanner";

export default function BusinessCardsPage() {
  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold mb-8">Business Card Scanner</h1>
      <BusinessCardScanner />
    </div>
  );
}
```

---

### 3. API Endpoints Available

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/process` | POST | Process single business card image |
| `/api/batch` | POST | Process multiple cards |
| `/api/health` | GET | Health check |

#### Single Card Request:
```javascript
const formData = new FormData();
formData.append('image', file);

const response = await fetch('https://your-api.onrender.com/api/process', {
  method: 'POST',
  body: formData
});

const result = await response.json();
```

#### Response Format:
```json
{
  "success": true,
  "contact_data": {
    "name": "John Smith",
    "first_name": "John",
    "last_name": "Smith",
    "title": "CEO",
    "company": "Acme Inc",
    "email": "john@acme.com",
    "phone": ["+1 555-123-4567"],
    "website": "www.acme.com",
    "company_logo": "https://logo.clearbit.com/acme.com",
    "industry": "technology",
    "confidence_score": 0.88
  },
  "field_confidence": {
    "name": 0.95,
    "email": 0.92,
    "phone": 0.85,
    "company": 0.90,
    "overall": 0.88,
    "quality": {
      "name": "verified",
      "email": "valid_format",
      "phone": "complete"
    }
  },
  "company_enrichment": {
    "logo_url": "https://logo.clearbit.com/acme.com",
    "domain": "acme.com",
    "industry": "technology",
    "linkedin_url": "https://linkedin.com/company/acme"
  },
  "ocr_method": "gemini_fallback",
  "processing_time_ms": 1234
}
```

---

### 4. CRM Integration

To save contacts to your SalesCentri CRM, modify the `addToContacts` function:

```typescript
const addToContacts = async (contact: ContactData) => {
  try {
    const response = await fetch('/api/contacts/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        firstName: contact.first_name,
        lastName: contact.last_name,
        email: contact.email,
        phone: contact.phone?.[0],
        company: contact.company,
        title: contact.title,
        website: contact.website,
        linkedin: contact.linkedin,
        industry: contact.industry,
        source: 'business_card_scan',
        confidence: contact.confidence_score
      })
    });
    
    if (response.ok) {
      toast.success(`Added ${contact.name} to contacts!`);
    }
  } catch (error) {
    toast.error('Failed to add contact');
  }
};
```

---

### 5. Pricing/Usage

| Component | Cost |
|-----------|------|
| EasyOCR (primary) | FREE |
| Gemini fallback | ~$0.0001/card |
| Clearbit Logo | FREE (no API key) |
| Company enrichment | FREE |

**Estimated cost:** $0.10 per 1,000 cards scanned

---

### 6. Features Included

✅ **Dual OCR:** EasyOCR (free) + Gemini fallback (accurate)
✅ **Company Logo:** Auto-fetched from Clearbit
✅ **Industry Detection:** Auto-detected from company name
✅ **LinkedIn URL:** Generated for company
✅ **Per-Field Confidence:** Know which fields are reliable
✅ **Quality Indicators:** "verified", "valid_format", "complete"
✅ **Processing Time:** Track performance

---

### 7. Where to Add in SalesCentri

Suggested locations:
1. **Dashboard → Tools → Business Card Scanner**
2. **Contacts → Import → Scan Business Cards**
3. **Lead Generation → Business Card Import**

The component is fully styled with Tailwind CSS to match your dark theme.
