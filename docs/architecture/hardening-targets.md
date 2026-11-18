# Hardening targets: from the lab to production

**Status:** draft of 17 Nov 2026 · decided by the maintainer ("Socle entreprise") · **Related:** ADR-020, ADR-021, ADR-023, `docs/sprints/S5-cadrage.md`

An enterprise does not build everything. It builds and tests the few protections that can fail a test, and it writes down what production would use for the rest, with the gap stated. A point enters S5 only if (a) a test can fail, (b) it reuses what exists, (c) it takes under 2 h. Otherwise it is a target below.

## A. Built and tested in S5 (hours are the author's estimate, about 8 h with section C)

| # | Item | Reuses | Test |
|---|---|---|---|
| 1 | Broker: mutual TLS, one certificate per client, ACL keyed on the certificate identity; no anonymous access, no plain-text port, TLS 1.2 at least | `pki-init` (ADR-023 point 7), extended with a lab CA for MQTT only (decided 17 Nov 2026) | the ADR-020 ACL FF, a check that port 1883 is not published, and a revocation test: a client revoked through the CRL is refused (whether Mosquitto reloads the CRL without a restart is not verified) |
| 2 | Broker limits (message size, connections, rate, no retained telemetry) and a last-will message so the edge going silent is visible | broker configuration | a flood and a cut, in the WAN scenario (FF-29) |
| 3 | Hardened containers for the new services (`edge`, broker, `jump`): non-root user, read-only root filesystem, all capabilities dropped, `no-new-privileges`, memory and process limits | compose | a static FF on the compose file, proved by a deliberate bad copy |
| 4 | One log format for new services: structured, UTC (ADR-010), one event per line | ADR-010 | a format check; collection is S24 |
| 5 | Threat model for the edge, broker and cloud boundary (TB-2), STRIDE | `threat-model-tb1a.md` as the model | a document, rows carried to FFs |

Retrofit of the existing services (3 and 4) is listed, not promised: some images may not run as non-root (the OpenPLC image is not checked).

## B. Production target, not built

| Subject | Lab today | Production target | Why not built |
|---|---|---|---|
| PKI | self-signed lab certificates | internal CA with an intermediate, rotation, revocation (CRL or OCSP), keys in an HSM or vault | needs infrastructure the lab does not have |
| Vendor access | OpenSSH `jump` (ADR-021) | a PAM product, approval tied to a change ticket, two-person approval on critical assets | OpenSSH stands in for it; the properties are the same, the product is not evaluated |
| Secrets | demo credentials (ADR-018) | a secrets vault | no real secret exists in the lab |
| Audit log | append-only volume | immutable storage with hash chaining | tamper-evidence needs a separate trust domain |
| Zone separation | DMZ and supervisory are separated by Docker network membership (no filtering inside a network), pinned by FF-22 | a filtering firewall between each pair of zones, allow-list by source, destination and port, logged | one firewall exists in the lab (`fw-cell`), a second adds a service without a new property |
| OT to IT boundary | logical, outbound only (ADR-005) | a hardware data diode for high SL-T zones | hardware |
| PLC program | signature check after load | baseline hash, management of change | no change process in a lab |
| Images | digest, SBOM, scan (FF-20) | signed images and an admission policy | later sprint |
| Time | gateway clock stamps `ts_src` | NTP or PTP on the OT network, drift alarm | assumption stated in ADR-020 |

## C. Reading across to the standards (to verify)

IEC 62443-3-3 requirement numbers are from memory and must be checked against the standard before they are cited: PKI and certificates (SR 1.8, 1.9), auditable events and timestamps (SR 2.8, 2.11), segmentation (SR 5.1). NIST SP 800-82 and the Purdue model are the reading frames recruiters know: `edge` and the broker sit in the DMZ (level 3.5). Vendor names above are examples, not an evaluation.

## Limits to state

The lab network is not a firewall. The author wrote the code, the expected results and this table: agreement with the requirement, not independent proof.
