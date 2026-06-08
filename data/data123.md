# Emerson CSER-2000 Series Gas Compressor
## Operations & Maintenance Manual
### Document No: EMR-CSER2000-OM-REV4
### Effective Date: January 2024

---

## 1. Equipment Overview

The Emerson CSER-2000 is a two-stage reciprocating gas compressor designed for natural gas gathering, transmission, and sales gas boosting applications in oil and gas production facilities. It is rated for continuous duty in upstream and midstream environments.

**Key Specifications:**

| Parameter | Value |
|---|---|
| Model | CSER-2000 |
| Type | Double-acting reciprocating |
| Rated horsepower | 2,500 HP |
| Rated speed | 1,200 RPM |
| Number of cylinders | 4 (2 per stage) |
| Design suction pressure | 150–250 psi |
| Design discharge pressure | 500–700 psi |
| Max compression ratio | 3.5 |
| Lube oil system | Force-feed, pressurised |
| Design service life | 30 years |

---

## 2. Normal Operating Parameters

The following ranges represent healthy, steady-state operation under typical field conditions. Readings outside these ranges should be logged and investigated.

### 2.1 Pressure Parameters

| Parameter | Normal Range | Advisory Threshold | Alarm Threshold |
|---|---|---|---|
| Suction pressure | 200–220 psi | < 190 psi | < 175 psi |
| Discharge pressure | 620–660 psi | < 600 psi or > 680 psi | < 580 psi or > 700 psi |
| Compression ratio | 2.9–3.1 | > 3.3 or < 2.7 | > 3.5 or < 2.5 |
| Lube oil pressure | 45–55 psi | < 40 psi | < 35 psi |

### 2.2 Temperature Parameters

| Parameter | Normal Range | Advisory Threshold | Alarm Threshold |
|---|---|---|---|
| Inlet (suction) gas temperature | 70–90°F | > 100°F | > 110°F |
| Discharge gas temperature | 245–265°F | > 275°F | > 300°F |
| Lube oil temperature | 175–190°F | > 195°F | > 210°F |
| Cylinder jacket cooling water out | 140–155°F | > 165°F | > 175°F |

### 2.3 Vibration Parameters (ISO 10816-6)

| Parameter | Normal Range | Advisory Threshold | Alarm Threshold |
|---|---|---|---|
| Frame vibration – X axis | 3.0–5.5 mm/s RMS | > 7.0 mm/s | > 10.0 mm/s |
| Frame vibration – Y axis | 2.0–4.0 mm/s RMS | > 7.0 mm/s | > 10.0 mm/s |
| Frame vibration – Z axis | 1.5–3.5 mm/s RMS | > 6.0 mm/s | > 9.0 mm/s |

### 2.4 Electrical & Mechanical Parameters

| Parameter | Normal Range | Advisory Threshold | Alarm Threshold |
|---|---|---|---|
| Motor current | 285–325 A | > 345 A | > 370 A |
| Shaft speed | 1,195–1,205 RPM | < 1,180 or > 1,220 RPM | < 1,150 or > 1,240 RPM |
| Power output | 355–385 kW | > 400 kW | > 420 kW |

---

## 3. Fault Signature Guide

### 3.1 Discharge Valve Wear or Fouling

**Description:** One of the most common failure modes on reciprocating compressors. Valve wear reduces sealing efficiency, causing hot gas recirculation and increased cylinder temperature.

**Indicator Pattern:**
- Discharge temperature rising above 275°F (advisory), trending toward alarm
- Compression ratio declining (discharge pressure falling relative to suction)
- Frame vibration increasing on X-axis, typically 6.5–8.5 mm/s range
- Lube oil temperature elevated (secondary effect of increased cylinder heat)
- Power draw may increase as efficiency drops

**Typical Progression:** Gradual over 2–6 weeks from initial onset to advisory breach. If untreated, reaches alarm levels within 4–8 additional weeks and risks unplanned shutdown.

**Recommended Action:** Inspect and replace discharge valve assemblies (seats, plates, springs) within 14 days of advisory breach. Do not defer past alarm threshold.

**Reference:** Section 6.2 – Valve Assembly Inspection and Replacement

---

### 3.2 Suction Valve Failure

**Indicator Pattern:**
- Suction pressure dropping at inlet
- Low compression ratio
- Increased cylinder knock noise (audible)
- Discharge temperature mildly elevated

**Recommended Action:** Emergency shutdown and valve replacement if suction pressure drops below 175 psi. Can be deferred 48–72 hours if advisory only, with close monitoring.

---

### 3.3 Piston Ring Wear

**Indicator Pattern:**
- Gradual decline in compression ratio over months
- Increased lube oil consumption
- Elevated crankcase pressure
- Slight increase in power draw

**Recommended Action:** Schedule piston ring replacement at next planned outage. Not typically an emergency unless combined with other faults.

---

### 3.4 Lube Oil System Degradation

**Indicator Pattern:**
- Lube oil temperature rising above 195°F (advisory)
- Lube oil pressure declining
- Possible increase in vibration (loss of film lubrication)

**Recommended Action:** Check lube oil cooler for fouling. Sample lube oil for viscosity and contamination. Replace oil and filters if contamination found. Inspect oil pump if pressure decline is confirmed.

---

### 3.5 Combined Advisory Pattern — High-Risk Scenario

**When to escalate immediately:** If two or more of the following occur simultaneously, escalate to maintenance lead and schedule inspection within 7 days:

- Discharge temperature > 275°F AND
- Frame vibration (X) > 7.0 mm/s AND
- Compression ratio < 2.85

This combination indicates probable discharge valve failure with secondary thermal stress. Risk of unplanned shutdown within 2–4 weeks if not addressed. Estimated production loss on unplanned shutdown: 8–12 MMSCFD ($40,000–$55,000/day at current gas prices).

---

## 4. Preventive Maintenance Schedule

| Interval | Tasks |
|---|---|
| 250 hours | Lube oil sample, filter check, visual inspection |
| 2,000 hours | Lube oil and filter change, valve visual inspection, packing check |
| 8,000 hours | Full valve inspection and replacement if worn, piston rod runout check, cylinder liner measurement |
| 12 months | Annual inspection: all of the above plus alignment check, coupling inspection, safety system test |
| 5 years | Major overhaul: cylinder rebore assessment, crankshaft inspection, all seals and gaskets |

---

## 5. Inspection Intervals for Valve Assemblies

Valve assemblies are the highest-wear components on the CSER-2000 and the most common cause of unplanned downtime.

- **Standard replacement interval:** 8,000 operating hours or 12 months, whichever comes first
- **Advisory threshold interval:** Inspect within 14 days of any discharge temperature advisory (>275°F)
- **Alarm threshold interval:** Immediate shutdown and inspection if discharge temperature exceeds 300°F

> **Note:** If the last valve inspection was more than 12 months ago and discharge temperature is trending upward, treat as an advisory condition regardless of whether the threshold has been crossed.

---

## 6. Troubleshooting Reference

### 6.1 High Discharge Temperature

| Cause | Distinguishing Features | Corrective Action |
|---|---|---|
| Discharge valve wear/fouling | Rising vibration X, declining compression ratio | Inspect/replace discharge valves |
| High inlet gas temperature | Inlet temp > 90°F, all other params normal | Check gas cooler or separator upstream |
| Insufficient cooling water flow | Jacket water outlet temp elevated | Check cooling water flow rate and temperature |
| Overloaded cylinder | High motor current, high compression ratio | Check downstream pressure; adjust setpoints |

### 6.2 Valve Assembly Inspection and Replacement

1. Isolate and depressurize the cylinder per lockout/tagout procedure
2. Remove valve cover and extract valve assembly
3. Inspect valve plates for cracks, erosion, and carbon deposits
4. Inspect valve seats for wear, pitting, or erosion
5. Check valve springs for set or fracture
6. Measure valve lift — nominal 0.090 in; replace if below 0.075 in
7. Replace complete valve assembly if any component fails inspection
8. Torque valve cover bolts to 185 ft-lb in cross pattern
9. Pressure test before restart

**Estimated downtime per cylinder:** 6–8 hours
**Parts cost (full valve assembly):** $1,800–$2,400 per cylinder
**Total for 4-cylinder replacement:** ~$8,000–$12,000 including labour

---

## 7. Spare Parts — Critical Stock Recommendation

| Part | Part Number | Recommended Stock Qty |
|---|---|---|
| Discharge valve assembly | CSER-DVA-200 | 4 (1 per cylinder) |
| Suction valve assembly | CSER-SVA-200 | 4 (1 per cylinder) |
| Valve springs (set of 8) | CSER-VS-08 | 2 sets |
| Piston rings (set) | CSER-PR-SET | 1 set |
| Packing rings | CSER-PKG-SET | 2 sets |
| Lube oil filter | CSER-LOF-01 | 6 |

---

## 8. Safety & Regulatory Compliance

This equipment is subject to the following regulations and standards:

- **API 618** – Reciprocating Compressors for Petroleum, Chemical, and Gas Industry Services
- **API 670** – Machinery Protection Systems
- **ISO 10816-6** – Mechanical vibration evaluation of machine vibration
- **OSHA 29 CFR 1910.119** – Process Safety Management of Highly Hazardous Chemicals
- **ASME B31.3** – Process Piping

All maintenance activities must be performed by qualified personnel following site-specific lockout/tagout and hot work procedures.

---

*For technical support, contact Emerson Process Management Field Services: +1-800-833-8314*
*Document controlled. Latest version available at emerson.com/oilandgas*
