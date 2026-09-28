import { AuditReport } from '../types/audit';

export const DEMO_AUDIT_ECOMMERCE: AuditReport = {
  id: 'aud_demo_ecom_01',
  site: 'https://apex-cine-gear.example.com',
  audited_at: '2026-09-27T18:30:00Z',
  site_archetype: 'ecommerce',
  pages_audited: 8,
  pages_discovered: 34,
  crawl_duration_seconds: 4.82,
  summary: {
    total_findings: 4,
    critical: 0,
    high: 2,
    medium: 1,
    low: 1,
    info: 0,
  },
  findings: [
    {
      id: 'F-001',
      title: 'Product specifications and pricing missing from initial HTML response',
      category: 'machine_readability',
      severity: 'high',
      confidence: 'high',
      observation: 'Core commercial facts (price: $4,999.00 USD, sensor size: Full-Frame 8K, mount: PL Mount) are absent from raw server response and injected purely client-side via JavaScript.',
      evidence: `Target URL: https://apex-cine-gear.example.com/products/cinema-camera-8k
Initial HTTP Body Text (26 chars):
  <div id="app">Loading camera details...</div>

Rendered DOM Extraction (248 chars):
  <div id="app">
    <h1>Cinema Camera 8K Pro</h1>
    <p class="price">$4,999.00 USD</p>
    <div class="specs">8K Super 35 CMOS Sensor, Dual Native ISO 800/3200</div>
  </div>

Missing in Raw HTML: ["$4,999.00", "Full-Frame 8K", "PL Mount", "Dual Native ISO"]`,
      root_cause: 'Product attributes, pricing, and technical specifications are loaded asynchronously via client-side JavaScript hydration without Server-Side Rendering (SSR) or Static Site Generation (SSG).',
      impact: 'Automated AI retrieval systems, web crawlers, and LLM search agents inspecting only initial HTTP response payloads cannot ingest pricing or core specifications, leading to hallucinated or missing catalog information.',
      detection_method: 'deterministic',
      affected_urls: [
        'https://apex-cine-gear.example.com/products/cinema-camera-8k',
        'https://apex-cine-gear.example.com/products/anamorphic-lens-50mm'
      ],
      suggested_action: {
        summary: 'Implement Server-Side Rendering (SSR) for all product detail pages and deliver canonical pricing in server-rendered HTML.',
        priority: 'high',
        implementation_details: 'Render product title, description, price, and specs inside initial HTML markup before client-side hydration mounts.'
      }
    },
    {
      id: 'F-002',
      title: 'Conflict between JSON-LD structured price and visible page pricing',
      category: 'structured_data',
      severity: 'high',
      confidence: 'high',
      observation: 'The schema.org Product Offer JSON-LD specifies price: 1999.00 USD, whereas visible rendered body text states $4,999.00 USD.',
      evidence: `Target URL: https://apex-cine-gear.example.com/products/cinema-camera-8k
Embedded JSON-LD Block:
  {
    "@context": "https://schema.org",
    "@type": "Product",
    "name": "Cinema Camera 8K Pro",
    "offers": {
      "@type": "Offer",
      "price": "1999.00",
      "priceCurrency": "USD",
      "availability": "https://schema.org/InStock"
    }
  }

Visible DOM Text Price:
  "$4,999.00 USD" (Differs by $3,000.00)`,
      root_cause: 'Hardcoded legacy price metadata in server template JSON-LD script tag was not updated when live product catalog pricing changed.',
      impact: 'AI agents and search knowledge graphs extract conflicting commercial facts, degrading entity trustworthiness and presenting incorrect pricing to potential buyers.',
      detection_method: 'deterministic',
      affected_urls: [
        'https://apex-cine-gear.example.com/products/cinema-camera-8k'
      ],
      suggested_action: {
        summary: 'Synchronize JSON-LD Product Offer price values dynamically with the active inventory database.',
        priority: 'high',
        implementation_details: 'Bind schema.org price and priceCurrency to the exact backend product model attributes used for rendered visual copy.'
      }
    },
    {
      id: 'F-003',
      title: 'Product detail page terminates with dead-end navigation',
      category: 'on_site_engagement',
      severity: 'medium',
      confidence: 'high',
      observation: 'Product page lacks contextual next-step navigation, related product links, or direct purchase pathways in HTML markup.',
      evidence: `Target URL: https://apex-cine-gear.example.com/products/anamorphic-lens-50mm
Total Internal Links Discovered: 0
Missing Structural Elements:
  - Add to Cart / Buy Now CTA
  - Related Accessories Section
  - Contact Specialist link`,
      root_cause: 'Footer and navigation markup are rendered within an unhydrated iframe or dynamic portal omitting standard semantic internal hyperlinks.',
      impact: 'Human visitors and navigational AI agents encounter dead-ends, drastically reducing conversion probability and engagement depth.',
      detection_method: 'heuristic',
      affected_urls: [
        'https://apex-cine-gear.example.com/products/anamorphic-lens-50mm'
      ],
      suggested_action: {
        summary: 'Provide contextual primary CTAs and semantic internal links to related catalog categories or accessories.',
        priority: 'medium',
        implementation_details: 'Ensure all conversion triggers and related catalog links use semantic standard <a href="..."> elements.'
      }
    },
    {
      id: 'F-004',
      title: 'Robots.txt restricts AI crawler access to documentation subpaths',
      category: 'crawlability',
      severity: 'low',
      confidence: 'high',
      observation: 'Robots.txt disallows GPTBot and ClaudeBot from accessing /specs and /manuals directories.',
      evidence: `Robots.txt URL: https://apex-cine-gear.example.com/robots.txt
Directive Extract:
  User-agent: GPTBot
  Disallow: /specs/
  Disallow: /manuals/
  
  User-agent: ClaudeBot
  Disallow: /specs/`,
      root_cause: 'Overly broad bot exclusion rules applied to technical documentation and specification subdirectories.',
      impact: 'AI answering engines cannot access authoritative product manuals to answer detailed customer support inquiries.',
      detection_method: 'deterministic',
      affected_urls: [
        'https://apex-cine-gear.example.com/robots.txt'
      ],
      suggested_action: {
        summary: 'Review bot exclusion policy to permit AI indexing of public technical specification sheets.',
        priority: 'low',
        implementation_details: 'Update robots.txt directives to allow AI user agents access to /specs/ if public discoverability is desired.'
      }
    }
  ],
  proactive_recommendations: [
    {
      id: 'REC-001',
      title: 'Entity Disambiguation via Authoritative sameAs URIs',
      opportunity: 'The Organization schema defines brand name "Apex Cine Gear" but omits external sameAs authority links to disambiguate the brand in universal knowledge graphs.',
      suggested_action: {
        summary: 'Add authoritative registry links (such as official Wikipedia, Wikidata, or LinkedIn organization URLs) to the root Organization JSON-LD.',
        priority: 'low',
        implementation_details: 'Add "sameAs": ["https://www.wikidata.org/wiki/...", "https://www.linkedin.com/company/..."] inside Organization schema block.'
      }
    }
  ],
  pages: [
    {
      url: 'https://apex-cine-gear.example.com/',
      normalized_url: 'https://apex-cine-gear.example.com/',
      status_code: 200,
      response_time_ms: 18.4,
      page_archetype: 'homepage',
      is_primary_page: true,
      title: 'Apex Cine Gear | Professional Cinematography Solutions',
      meta_description: 'Precision optics, digital cinema cameras, and professional filmmaking gear engineered for creators.',
      canonical_url: 'https://apex-cine-gear.example.com/',
      headings_count: 5,
      headings: [
        { tag: 'h1', level: 1, text: 'Engineered for Cinematic Vision', dom_index: 0 },
        { tag: 'h2', level: 2, text: 'Featured Cinema Cameras', dom_index: 1 },
        { tag: 'h2', level: 2, text: 'Anamorphic Optics', dom_index: 2 },
        { tag: 'h3', level: 3, text: 'Global Service & Support', dom_index: 3 },
      ],
      schema_types: ['Organization', 'WebSite'],
      internal_links_count: 14,
      external_links_count: 3,
      extracted_facts: { brand: 'Apex Cine Gear', founded: '2018' },
    },
    {
      url: 'https://apex-cine-gear.example.com/products/cinema-camera-8k',
      normalized_url: 'https://apex-cine-gear.example.com/products/cinema-camera-8k',
      status_code: 200,
      response_time_ms: 24.2,
      page_archetype: 'product_detail',
      is_primary_page: true,
      title: 'Cinema Camera 8K Pro | Apex Cine Gear',
      meta_description: 'Full-frame 8K digital cinema camera with dual native ISO and 16 stops of dynamic range.',
      canonical_url: 'https://apex-cine-gear.example.com/products/cinema-camera-8k',
      headings_count: 3,
      headings: [
        { tag: 'h1', level: 1, text: 'Cinema Camera 8K Pro', dom_index: 0 },
        { tag: 'h2', level: 2, text: 'Technical Specifications', dom_index: 1 },
        { tag: 'h2', level: 2, text: 'Accessories & Rigs', dom_index: 2 }
      ],
      schema_types: ['Product', 'Offer'],
      internal_links_count: 8,
      external_links_count: 1,
      extracted_facts: { price_visible: '$4,999.00', price_schema: '$1,999.00' },
    },
    {
      url: 'https://apex-cine-gear.example.com/products/anamorphic-lens-50mm',
      normalized_url: 'https://apex-cine-gear.example.com/products/anamorphic-lens-50mm',
      status_code: 200,
      response_time_ms: 22.8,
      page_archetype: 'product_detail',
      is_primary_page: false,
      title: '50mm T2.0 Anamorphic Prime | Apex Cine Gear',
      meta_description: '2x squeeze anamorphic prime lens with organic oval bokeh and controlled horizontal flare.',
      canonical_url: 'https://apex-cine-gear.example.com/products/anamorphic-lens-50mm',
      headings_count: 2,
      headings: [
        { tag: 'h1', level: 1, text: '50mm T2.0 Anamorphic Prime', dom_index: 0 },
        { tag: 'h2', level: 2, text: 'Optical Performance', dom_index: 1 }
      ],
      schema_types: ['Product'],
      internal_links_count: 0,
      external_links_count: 0,
      extracted_facts: { focal_length: '50mm', max_aperture: 'T2.0' },
    },
    {
      url: 'https://apex-cine-gear.example.com/pricing',
      normalized_url: 'https://apex-cine-gear.example.com/pricing',
      status_code: 200,
      response_time_ms: 19.5,
      page_archetype: 'pricing',
      is_primary_page: true,
      title: 'Production Equipment Rental & Purchase Pricing',
      meta_description: 'Transparent pricing for direct camera purchases and production rental packages.',
      canonical_url: 'https://apex-cine-gear.example.com/pricing',
      headings_count: 4,
      headings: [
        { tag: 'h1', level: 1, text: 'Pricing & Rental Tiers', dom_index: 0 },
        { tag: 'h2', level: 2, text: 'Direct Purchase Packages', dom_index: 1 },
        { tag: 'h2', level: 2, text: 'Daily & Weekly Rentals', dom_index: 2 }
      ],
      schema_types: ['PriceSpecification'],
      internal_links_count: 11,
      external_links_count: 0,
      extracted_facts: {},
    }
  ]
};

export const DEMO_AUDIT_HEALTHY: AuditReport = {
  id: 'aud_demo_healthy_01',
  site: 'https://stellar-optical.example.com',
  audited_at: '2026-09-27T19:00:00Z',
  site_archetype: 'corporate',
  pages_audited: 5,
  pages_discovered: 12,
  crawl_duration_seconds: 2.14,
  summary: {
    total_findings: 0,
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    info: 0,
  },
  findings: [],
  proactive_recommendations: [],
  pages: [
    {
      url: 'https://stellar-optical.example.com/',
      normalized_url: 'https://stellar-optical.example.com/',
      status_code: 200,
      response_time_ms: 14.2,
      page_archetype: 'homepage',
      is_primary_page: true,
      title: 'Stellar Optical Systems | Precision Satellite Payloads',
      meta_description: 'Industry-leading orbital optical instruments and high-throughput laser communication sensors.',
      canonical_url: 'https://stellar-optical.example.com/',
      headings_count: 3,
      headings: [
        { tag: 'h1', level: 1, text: 'Stellar Optical Systems', dom_index: 0 },
        { tag: 'h2', level: 2, text: 'Orbital Sensors & Payloads', dom_index: 1 },
        { tag: 'h2', level: 2, text: 'Flight Proven Architecture', dom_index: 2 }
      ],
      schema_types: ['Organization', 'WebSite'],
      internal_links_count: 9,
      external_links_count: 2,
      extracted_facts: { copyright_year: '2026' }
    }
  ]
};
