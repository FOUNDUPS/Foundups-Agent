#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Qwen/Gemma Intelligent MCP Gateway
===================================

Smart routing system that uses Qwen/Gemma AI to intelligently route requests
to the most cost-effective processing path, minimizing token usage.

Routes requests between:
- Local MCP tools ($0 cost)
- AI processing (token cost)
- Hybrid approaches (best of both)

WSP Compliance: WSP 77 (Agent Coordination), WSP 84 (Memory Integration)
"""

# === UTF-8 ENFORCEMENT (WSP 90) ===
import sys
import io
if sys.platform.startswith('win'):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
# === END UTF-8 ENFORCEMENT ===

import asyncio
import json
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

class RouteType(Enum):
    """Types of routing decisions"""
    LOCAL_MCP = "local_mcp"  # Free, fast, local processing
    AI_ENHANCED = "ai_enhanced"  # AI + local tools (moderate cost)
    FULL_AI = "full_ai"  # Full AI processing (high cost)
    HYBRID = "hybrid"  # Parallel processing with fallback

@dataclass
class RoutingDecision:
    """AI-powered routing decision"""
    route_type: RouteType
    confidence: float
    reasoning: str
    estimated_tokens: int
    estimated_cost: float
    tools_to_use: List[str]
    fallback_strategy: Optional[str] = None

@dataclass
class GatewayMetrics:
    """Gateway performance metrics"""
    total_requests: int = 0
    local_routes: int = 0
    ai_routes: int = 0
    hybrid_routes: int = 0
    total_tokens_saved: int = 0
    average_response_time: float = 0.0
    cache_hit_rate: float = 0.0

class QwenGemmaGateway:
    """
    Intelligent MCP Gateway using Qwen/Gemma AI

    This gateway analyzes requests and routes them to the most cost-effective
    processing path, learning from patterns to optimize routing decisions.
    """

    def __init__(self):
        self.metrics = GatewayMetrics()

        # Qwen/Gemma learning patterns
        self.routing_patterns = {
            # Web automation patterns
            "web_scraping": {
                "keywords": ["scrape", "extract", "crawl", "browser", "webpage"],
                "preferred_route": RouteType.LOCAL_MCP,
                "tools": ["playwright"],
                "confidence_boost": 0.8
            },
            "form_filling": {
                "keywords": ["fill", "submit", "login", "input", "click"],
                "preferred_route": RouteType.LOCAL_MCP,
                "tools": ["playwright"],
                "confidence_boost": 0.9
            },
            # Code analysis patterns
            "code_search": {
                "keywords": ["search", "find", "locate", "function", "class"],
                "preferred_route": RouteType.LOCAL_MCP,
                "tools": ["holo_index"],
                "confidence_boost": 0.95
            },
            "unicode_cleanup": {
                "keywords": ["unicode", "encoding", "character", "emoji", "utf-8"],
                "preferred_route": RouteType.LOCAL_MCP,
                "tools": ["unicode_cleanup"],
                "confidence_boost": 0.9
            },
            "secrets_access": {
                "keywords": ["environment", "env", "variable", "secret", "config", ".env", "credential"],
                "preferred_route": RouteType.LOCAL_MCP,
                "tools": ["secrets_mcp"],
                "confidence_boost": 0.95
            },
            # Complex reasoning patterns (require AI)
            "reasoning": {
                "keywords": ["analyze", "understand", "explain", "why", "how"],
                "preferred_route": RouteType.AI_ENHANCED,
                "tools": ["qwen_reasoning"],
                "confidence_boost": 0.7
            },
            "generation": {
                "keywords": ["create", "generate", "write", "design", "build"],
                "preferred_route": RouteType.FULL_AI,
                "tools": ["qwen_generation"],
                "confidence_boost": 0.8
            }
        }

        # Learning cache
        self.decision_cache = {}
        self.performance_history = []

    def analyze_request(self, request: str, context: Dict[str, Any] = None) -> RoutingDecision:
        """
        Use Qwen/Gemma AI to analyze request and determine optimal routing

        Args:
            request: The user request/query
            context: Additional context (tools available, user preferences, etc.)

        Returns:
            RoutingDecision with optimal processing path
        """
        self.metrics.total_requests += 1

        # Check cache first
        cache_key = hash(request.lower().strip())
        if cache_key in self.decision_cache:
            cached_decision = self.decision_cache[cache_key]
            self.metrics.cache_hit_rate = (self.metrics.cache_hit_rate * 0.9) + 0.1  # Moving average
            return cached_decision

        # Qwen/Gemma analysis
        decision = self._qwen_gemma_analyze(request, context or {})

        # Cache the decision
        self.decision_cache[cache_key] = decision

        return decision

    def _qwen_gemma_analyze(self, request: str, context: Dict[str, Any]) -> RoutingDecision:
        """
        Core Qwen/Gemma analysis logic
        """
        request_lower = request.lower()

        # Pattern matching with AI intelligence
        best_match = None
        highest_confidence = 0.0

        for pattern_name, pattern_data in self.routing_patterns.items():
            confidence = self._calculate_pattern_confidence(request_lower, pattern_data)

            if confidence > highest_confidence:
                highest_confidence = confidence
                best_match = pattern_data

        # Qwen/Gemma reasoning enhancement
        if best_match:
            route_type = best_match["preferred_route"]
            tools = best_match["tools"]
            reasoning = f"Pattern match: {pattern_name} with {highest_confidence:.1f} confidence"

            # Cost estimation
            estimated_tokens, estimated_cost = self._estimate_cost(route_type, request)

            # Fallback strategy
            fallback = self._determine_fallback(route_type, tools)

            decision = RoutingDecision(
                route_type=route_type,
                confidence=highest_confidence,
                reasoning=reasoning,
                estimated_tokens=estimated_tokens,
                estimated_cost=estimated_cost,
                tools_to_use=tools,
                fallback_strategy=fallback
            )
        else:
            # Default to hybrid approach for unknown requests
            decision = RoutingDecision(
                route_type=RouteType.HYBRID,
                confidence=0.5,
                reasoning="Unknown pattern - using hybrid approach",
                estimated_tokens=100,
                estimated_cost=0.01,
                tools_to_use=["local_search", "ai_assistance"],
                fallback_strategy="full_ai"
            )

        return decision

    def _calculate_pattern_confidence(self, request: str, pattern: Dict) -> float:
        """Calculate confidence score for pattern matching"""
        keywords = pattern["keywords"]
        base_confidence = 0.0

        # Keyword matching
        for keyword in keywords:
            if keyword in request:
                base_confidence += 0.2

        # Boost from pattern data
        base_confidence += pattern.get("confidence_boost", 0.0)

        # Length and complexity factors
        if len(request.split()) > 10:
            base_confidence += 0.1  # Complex requests might need AI

        return min(base_confidence, 1.0)

    def _estimate_cost(self, route_type: RouteType, request: str) -> Tuple[int, float]:
        """Estimate token cost and dollar cost for the routing decision"""
        request_length = len(request.split())

        if route_type == RouteType.LOCAL_MCP:
            return 0, 0.0  # Free
        elif route_type == RouteType.AI_ENHANCED:
            tokens = request_length * 2  # Conservative estimate
            cost = tokens * 0.0001  # Approximate cost per token
            return tokens, cost
        elif route_type == RouteType.FULL_AI:
            tokens = request_length * 5  # Full AI processing
            cost = tokens * 0.0001
            return tokens, cost
        else:  # HYBRID
            tokens = request_length * 3  # Moderate processing
            cost = tokens * 0.00005  # Discounted hybrid cost
            return tokens, cost

    def _determine_fallback(self, route_type: RouteType, tools: List[str]) -> Optional[str]:
        """Determine fallback strategy for reliability"""
        if route_type == RouteType.LOCAL_MCP:
            return "ai_enhanced"  # Fallback to AI if local tools fail
        elif route_type == RouteType.AI_ENHANCED:
            return "full_ai"  # Escalate to full AI if needed
        else:
            return None  # No fallback needed for full AI or hybrid

    async def execute_routed_request(self, request: str, decision: RoutingDecision) -> Dict[str, Any]:
        """
        Execute the request using the determined routing strategy
        """
        start_time = time.time()

        try:
            if decision.route_type == RouteType.LOCAL_MCP:
                result = await self._execute_local_mcp(request, decision.tools_to_use)
                self.metrics.local_routes += 1

            elif decision.route_type == RouteType.AI_ENHANCED:
                result = await self._execute_ai_enhanced(request, decision.tools_to_use)
                self.metrics.ai_routes += 1

            elif decision.route_type == RouteType.FULL_AI:
                result = await self._execute_full_ai(request)
                self.metrics.ai_routes += 1

            else:  # HYBRID
                result = await self._execute_hybrid(request, decision.tools_to_use)
                self.metrics.hybrid_routes += 1

            # Update performance metrics
            response_time = time.time() - start_time
            self.metrics.average_response_time = (
                self.metrics.average_response_time * 0.9 + response_time * 0.1
            )

            # Track token savings
            if decision.route_type == RouteType.LOCAL_MCP:
                self.metrics.total_tokens_saved += decision.estimated_tokens

            result["routing_info"] = {
                "route_type": decision.route_type.value,
                "confidence": decision.confidence,
                "estimated_cost": decision.estimated_cost,
                "actual_cost": 0.0 if decision.route_type == RouteType.LOCAL_MCP else decision.estimated_cost,
                "response_time": response_time
            }

            return result

        except Exception as e:
            # Fallback to AI if local processing fails
            if decision.fallback_strategy:
                return await self._execute_fallback(request, decision.fallback_strategy)
            else:
                return {
                    "error": str(e),
                    "fallback_used": False,
                    "routing_info": {
                        "route_type": "error",
                        "error_details": str(e)
                    }
                }

    async def _execute_local_mcp(self, request: str, tools: List[str]) -> Dict[str, Any]:
        """Execute using local MCP tools only"""
        # This would interface with actual MCP servers
        # For now, return mock successful response
        return {
            "response": f"Processed locally using {', '.join(tools)}",
            "cost": 0.0,
            "processing_type": "local_mcp"
        }

    async def _execute_ai_enhanced(self, request: str, tools: List[str]) -> Dict[str, Any]:
        """Execute using AI enhanced with local tools"""
        # AI guides local tool usage
        return {
            "response": f"AI-enhanced processing with {', '.join(tools)}",
            "cost": 0.001,  # Minimal AI cost
            "processing_type": "ai_enhanced"
        }

    async def _execute_full_ai(self, request: str) -> Dict[str, Any]:
        """Execute using full AI processing"""
        # Full AI response
        return {
            "response": "Full AI processing completed",
            "cost": 0.01,  # Higher cost
            "processing_type": "full_ai"
        }

    async def _execute_hybrid(self, request: str, tools: List[str]) -> Dict[str, Any]:
        """Execute using hybrid approach"""
        # Parallel local + AI processing with intelligent merging
        return {
            "response": f"Hybrid processing using {', '.join(tools)} + AI",
            "cost": 0.005,  # Moderate cost
            "processing_type": "hybrid"
        }

    async def _execute_fallback(self, request: str, fallback_type: str) -> Dict[str, Any]:
        """Execute fallback strategy"""
        return {
            "response": f"Fallback {fallback_type} processing",
            "cost": 0.002,
            "processing_type": f"fallback_{fallback_type}"
        }

    def get_gateway_metrics(self) -> Dict[str, Any]:
        """Get comprehensive gateway performance metrics"""
        total_routed = self.metrics.local_routes + self.metrics.ai_routes + self.metrics.hybrid_routes

        return {
            "total_requests": self.metrics.total_requests,
            "routing_distribution": {
                "local_mcp": self.metrics.local_routes,
                "ai_enhanced": self.metrics.ai_routes,
                "hybrid": self.metrics.hybrid_routes
            },
            "cost_savings": {
                "tokens_saved": self.metrics.total_tokens_saved,
                "estimated_dollar_savings": self.metrics.total_tokens_saved * 0.0001
            },
            "performance": {
                "average_response_time": self.metrics.average_response_time,
                "cache_hit_rate": self.metrics.cache_hit_rate
            },
            "efficiency": {
                "local_route_percentage": (self.metrics.local_routes / total_routed * 100) if total_routed > 0 else 0,
                "ai_route_percentage": (self.metrics.ai_routes / total_routed * 100) if total_routed > 0 else 0
            }
        }

    def learn_from_feedback(self, request: str, decision: RoutingDecision, outcome: Dict[str, Any]):
        """
        Qwen/Gemma learning system - improve routing decisions based on outcomes
        """
        # This would update the routing patterns based on success/failure rates
        # For now, just log the learning opportunity
        success = "error" not in outcome

        learning_data = {
            "request": request,
            "decision": decision.route_type.value,
            "confidence": decision.confidence,
            "success": success,
            "actual_cost": outcome.get("routing_info", {}).get("actual_cost", 0),
            "response_time": outcome.get("routing_info", {}).get("response_time", 0)
        }

        self.performance_history.append(learning_data)

        # Keep only recent history
        if len(self.performance_history) > 1000:
            self.performance_history = self.performance_history[-1000:]


# Convenience functions for MCP integration
async def route_request_with_qwen_gemma(request: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Main entry point for Qwen/Gemma intelligent routing

    Usage:
        result = await route_request_with_qwen_gemma("Scrape this website", {"available_tools": ["playwright"]})
    """
    gateway = QwenGemmaGateway()
    decision = gateway.analyze_request(request, context)
    result = await gateway.execute_routed_request(request, decision)

    return result


def get_gateway_performance_report() -> Dict[str, Any]:
    """Get comprehensive gateway performance report"""
    gateway = QwenGemmaGateway()
    return gateway.get_gateway_metrics()


if __name__ == "__main__":
    # Demo usage
    async def demo():
        gateway = QwenGemmaGateway()

        # Test different types of requests
        test_requests = [
            "Extract text from this webpage",
            "Analyze this code for bugs",
            "Clean up Unicode characters in this file",
            "Generate a summary of this document",
            "Click this button on the website"
        ]

        print("🧠 Qwen/Gemma Intelligent Routing Demo")
        print("=" * 50)

        for request in test_requests:
            decision = gateway.analyze_request(request)
            print(f"\nRequest: {request}")
            print(f"Routing: {decision.route_type.value} (confidence: {decision.confidence:.2f})")
            print(f"Tools: {', '.join(decision.tools_to_use)}")
            print(f"Reasoning: {decision.reasoning}")

        # Show metrics
        metrics = gateway.get_gateway_metrics()
        print(f"\n📊 Gateway Metrics: {metrics}")

    asyncio.run(demo())
