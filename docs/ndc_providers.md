# Public NDC API Research

This note highlights airline distribution partners that expose publicly documented or sandbox-friendly NDC APIs. Use it as the starting point for prioritizing integrations beyond the existing Amadeus implementation.

## Provider Snapshots

| Provider | Access Model | Notable Capabilities | Getting Started |
| --- | --- | --- | --- |
| **Amadeus for Developers (Enterprise NDC)** | Paid commercial agreement with self-service sandbox | Offer & order management, seat maps, ancillaries, post-book servicing | Request NDC access via the Amadeus Enterprise program once sandbox evaluation is complete. |
| **Lufthansa Group NDC** | Free sandbox with registration; production requires accreditation | Direct airline content for Lufthansa, SWISS, Austrian, Brussels Airlines; rich content (fare families, ancillaries) | Register on the Lufthansa Group PartnerPlusBenefit or NDC Partner portal for credentials and docs. |
| **British Airways NDC** | Partner registration with sandbox credentials on approval | End-to-end offer/order APIs, rich media, disruption notifications | Apply via the BA NDC portal; sandbox keys are issued after business approval. |
| **American Airlines NDC (AA Connect)** | Partner agreement, sandbox supported | Shopping, booking, post-ticket servicing, continuous pricing | Submit a request through AA Connect; requires IATA agency number but sandbox credentials are provided after validation. |
| **Duffel** | Self-serve developer accounts with test environment | Aggregated NDC content from multiple airlines, payments, post-book servicing | Create a Duffel developer account to retrieve API keys and explore the test console. |
| **Travelfusion** | Commercial contract, test environment accessible after onboarding | Aggregated LCC and NDC content, fare bundles, ancillaries | Contact Travelfusion sales for credentials; sandbox keys typically issued during contracting. |

## Evaluation Notes

1. **Commercial Readiness** – Lufthansa Group and Duffel provide the fastest way to experiment thanks to immediate or rapid sandbox access. Amadeus, British Airways, and American Airlines require commercial vetting but unlock deeper servicing flows once approved.
2. **Content Breadth** – Aggregators such as Duffel and Travelfusion accelerate coverage across carriers while airline-direct APIs unlock the richest fare families, ancillaries, and disruption handling.
3. **Certification Requirements** – Many airlines ask for IATA accreditation or proof of agency status before issuing production keys. Build a reusable compliance package (legal entity docs, IATA numbers, PCI posture) to streamline approvals.
4. **API Design Alignment** – All providers follow the core IATA NDC schema (Offer, Order, ServiceList endpoints) but differ in authentication, versioning, and optional fields. Design an abstraction layer that normalizes offers and orders so the UI/finance modules can remain provider-agnostic.

## Suggested Next Steps

1. **Prototype with Duffel or Lufthansa Group** – Both offer accessible sandboxes and comprehensive docs, making them ideal for validating our abstraction approach and UI needs.
2. **Map Capability Gaps** – Compare each provider's servicing coverage (refunds, exchanges, disruption notifications) to existing workflows to understand effort for parity with Amadeus.
3. **Plan Certification Timeline** – Document required agreements, fees, and lead times so sales can forecast when premium modules (e.g., airline-direct content) become sellable.
4. **Instrument Monitoring** – Incorporate provider health checks, rate-limit awareness, and booking reconciliation hooks so that multi-provider support remains reliable once live.

Keeping this research up to date ensures the product team can quickly evaluate which NDC partners to onboard as customers demand wider airline coverage.
