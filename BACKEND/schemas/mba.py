from pydantic import BaseModel
from typing import List


class AssociationRule(BaseModel):
    antecedent:  str        # item that triggers the rule  e.g. "Latte"
    consequent:  str        # item that follows            e.g. "Croissant"
    support:     float      # % of all orders containing both
    confidence:  float      # % of antecedent orders that also have consequent
    lift:        float      # how much more likely than random co-occurrence


class ProductPairCount(BaseModel):
    item_a:      str
    item_b:      str
    co_count:    int        # number of orders containing both


class BundleSuggestion(BaseModel):
    trigger_item:   str
    paired_item:    str
    confidence_pct: float
    lift:           float
    insight:        str     # human-readable sentence for the UI card


class MBAResult(BaseModel):
    rules:            List[AssociationRule]
    product_pairs:    List[ProductPairCount]
    bundle_suggestions: List[BundleSuggestion]
    total_orders_analysed: int