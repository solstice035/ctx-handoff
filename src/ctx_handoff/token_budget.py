"""Token counting and budget management."""

from typing import Dict


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses simple heuristic: ~4 characters per token.
    """
    return len(text) // 4


class TokenBudget:
    """Manages token budget allocation for snapshot content."""
    
    def __init__(self, total_budget: int):
        """Initialize with total token budget."""
        self.total = total_budget
        self.used = 0
        self.allocations: Dict[str, int] = {}
    
    @property
    def remaining(self) -> int:
        """Get remaining token budget."""
        return max(0, self.total - self.used)
    
    def can_allocate(self, tokens: int) -> bool:
        """Check if tokens can be allocated within budget."""
        return self.used + tokens <= self.total
    
    def allocate(self, tokens: int, category: str) -> bool:
        """
        Allocate tokens to a category.
        Returns True if successful, False if exceeds budget.
        """
        if not self.can_allocate(tokens):
            return False
        
        self.used += tokens
        self.allocations[category] = self.allocations.get(category, 0) + tokens
        return True
    
    def get_allocation(self, category: str) -> int:
        """Get tokens allocated to a category."""
        return self.allocations.get(category, 0)
    
    def get_usage_percentage(self) -> float:
        """Get percentage of budget used."""
        return (self.used / self.total * 100) if self.total > 0 else 0
