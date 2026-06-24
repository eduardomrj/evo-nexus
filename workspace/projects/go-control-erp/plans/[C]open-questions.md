
## go-lookup (extração CEP/CNPJ) — 2026-06-24
- [ ] CEP cache TTL no Redis: manter 30 dias ou alinhar aos 15 dias do CNPJ? — freshness/hit rate — Risk: low
- [ ] API key: única ou read/admin separadas (invalidar cache)? — segurança do DELETE cache — Risk: med
- [ ] Default de providers ativos do CNPJ após colapso de config — comportamento de fallback — Risk: med
- [ ] Ordem de migração account vs admin (.pth): remover wiring antes de deletar pacote físico? — pode quebrar account — Risk: med-high
- [ ] Contrato ADR-015 (ModuloEnvironmentUrl/manifest.json) para descoberta do go-lookup — registro no Platform Admin — Risk: med
- [ ] Local do repo go-lookup (git próprio em evo-projects/go-control/go-lookup/?) — Risk: low
