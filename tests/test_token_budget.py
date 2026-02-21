"""Tests for token budget management."""

import pytest
from ctx_handoff.token_budget import TokenBudget, estimate_tokens


def test_estimate_tokens():
    """Test token estimation."""
    text = "Hello, world!"
    tokens = estimate_tokens(text)
    
    # Should be roughly len(text) // 4
    assert tokens == len(text) // 4


def test_token_budget_allocation():
    """Test token budget allocation."""
    budget = TokenBudget(1000)
    
    assert budget.total == 1000
    assert budget.used == 0
    assert budget.remaining == 1000
    
    # Allocate some tokens
    assert budget.allocate(100, "test")
    assert budget.used == 100
    assert budget.remaining == 900
    
    # Allocate more
    assert budget.allocate(500, "test2")
    assert budget.used == 600
    assert budget.remaining == 400
    
    # Try to allocate too many
    assert not budget.allocate(500, "test3")
    assert budget.used == 600  # Should not change


def test_token_budget_can_allocate():
    """Test can_allocate check."""
    budget = TokenBudget(100)
    
    assert budget.can_allocate(50)
    assert budget.can_allocate(100)
    assert not budget.can_allocate(101)
    
    budget.allocate(50, "test")
    
    assert budget.can_allocate(50)
    assert not budget.can_allocate(51)


def test_token_budget_usage_percentage():
    """Test usage percentage calculation."""
    budget = TokenBudget(1000)
    
    assert budget.get_usage_percentage() == 0.0
    
    budget.allocate(250, "test")
    assert budget.get_usage_percentage() == 25.0
    
    budget.allocate(750, "test2")
    assert budget.get_usage_percentage() == 100.0
