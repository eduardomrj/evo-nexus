# Open Questions — core-services-independence

## core-services-independence — 2026-06-24
- [ ] Q1 — Onde mora o source do `platform-core`: subdir no repo admin (Opção A) vs repo separado (Opção B)? — Define versionamento/CI; padrão da org (SDK) é repo separado via git-tag — Risco: med — **bloqueia Fase 2**
- [ ] Q2 — Como o admin acessa o auth após remover `auth_central`: HTTP (`PLATFORM_AUTH_URL`) ou deixa de precisar? — Define se nasce contrato HTTP novo (exige security gate) — Risco: high
- [ ] Q3 — Namespace das apps no pacote: preservar `app_label` atual via namespace package `apps`, ou namespace próprio com `app_label` explícito? — Erro quebra 67+ migrations e ContentType — Risco: high — **decidir em 1.2 antes de 2.2**
- [ ] Q4 — Migrations de `auth_central` no histórico do admin ao remover: `--fake`, manter, ou squash? Bancos provisionados não podem regredir — Risco: med
