"""Model chains per purpose (V5-D22, docs/model-chain.md): which free OpenRouter models a call may use, in order.

A chain is a list of model ids; a purpose ("plan", "free", "wording", ...) names the chain it uses; an unknown purpose uses the default chain. The lineup of free models
rotates often, so the chains live in a JSON file (`api/llm/chains.json`, or the file `MODEL_CHAINS_PATH` names), not in code.

Safety rule, checked at load: every id in a chain must end in `:free`. OpenRouter bills a request by the model that ended up answering, so a paid id in a free chain
would spend money outside the ledger's reservation. A file that breaks the rule is refused with a message naming the chain and the id.

A PAID chains file (V5-D26) says so with `"paid": true` and may list paid ids (Claude through OpenRouter credits). It is a different file, read only when the
paid fallback is allowed and a cap is set (`OPENROUTER_PAID_CHAINS_PATH`), and every call through it is reserved and booked against that cap by the model the
call's purpose uses (`Chains.model_for_purpose`), so a paid id can never be sent outside the ledger. A paid file must not mix in `:free` ids: a free model
belongs in the free chains, where it is tried by its own provider.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).with_name("chains.json")
MAX_CHAIN = 6
"""A chain is sent to OpenRouter in groups of three (its fallback list takes at most three models), and at most two groups are tried."""


class ChainsError(ValueError):
    """The chains file cannot be used. The message names the problem."""


@dataclass(frozen=True)
class Chains:
    chains: dict[str, tuple[str, ...]]
    purposes: dict[str, str]
    default: str
    paid: bool = False
    """True for a paid chains file (V5-D26): its ids are billed, so its provider is built only behind the cap."""

    def for_purpose(self, purpose: str) -> tuple[str, ...]:
        """The ordered model ids for a call's purpose."""
        return self.chains[self.purposes.get(purpose, self.default)]

    def model_for_purpose(self, purpose: str) -> str:
        """The first model a call of this purpose is sent to: what the ledger reserves against. For a paid file this is the price that matters."""
        return self.for_purpose(purpose)[0]

    def first(self) -> str:
        """The first model of the default chain: what the ledger reserves against before the call, and what is booked if a reply does not name its model."""
        return self.chains[self.default][0]


def parse_chains(data: object) -> Chains:
    if not isinstance(data, dict):
        raise ChainsError("the chains file must be a JSON object")
    raw_chains = data.get("chains")
    raw_purposes = data.get("purposes")
    default = data.get("default")
    if not isinstance(raw_chains, dict) or not raw_chains:
        raise ChainsError('the chains file needs a non-empty "chains" object')
    if not isinstance(raw_purposes, dict):
        raise ChainsError('the chains file needs a "purposes" object')
    paid = data.get("paid", False)
    if not isinstance(paid, bool):
        raise ChainsError('"paid" must be true or false')
    chains: dict[str, tuple[str, ...]] = {}
    for name, ids in raw_chains.items():
        if not isinstance(ids, list) or not 1 <= len(ids) <= MAX_CHAIN:
            raise ChainsError(f'chain "{name}" must be a list of 1 to {MAX_CHAIN} model ids')
        for model in ids:
            if not paid and (not isinstance(model, str) or not model.endswith(":free")):
                raise ChainsError(f'chain "{name}" has "{model}": every id in a free chain must be a string ending in ":free"')
            if not isinstance(model, str) or not model.strip():
                raise ChainsError(f'chain "{name}" has "{model}": every id must be a non-empty string')
            if paid and model.endswith(":free"):
                raise ChainsError(f'chain "{name}" has "{model}": a paid chains file lists paid ids only (free ids belong in the free chains)')
        if len(set(ids)) != len(ids):
            raise ChainsError(f'chain "{name}" lists a model twice')
        chains[str(name)] = tuple(ids)
    purposes: dict[str, str] = {}
    for purpose, chain in raw_purposes.items():
        if chain not in chains:
            raise ChainsError(f'purpose "{purpose}" names an unknown chain "{chain}"')
        purposes[str(purpose)] = str(chain)
    if not isinstance(default, str) or default not in chains:
        raise ChainsError('"default" must name one of the chains')
    return Chains(chains=chains, purposes=purposes, default=default, paid=paid)


def load_chains(path: Path | None = None) -> Chains:
    target = path if path is not None else DEFAULT_PATH
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except OSError as exc:
        raise ChainsError(f"cannot read the chains file {target}: {exc.strerror or exc}") from exc
    except ValueError as exc:
        raise ChainsError(f"the chains file {target} is not valid JSON: {exc}") from exc
    return parse_chains(data)
