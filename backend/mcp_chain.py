"""
Maestra Backend - MCP Chaining Orchestrator

Chains multiple MCPs together for complex multi-step intelligence.
Enables session continuity by tracking context across MCP calls.

Patterns:
- Sequential: A → B → C (output of A feeds into B)
- Parallel: A + B → C (both run, results merged)
- Conditional: A → (if X) B else C
- Iterative: A → B → A (feedback loop)
"""

import logging
import asyncio
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

class ChainPattern(str, Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ITERATIVE = "iterative"

@dataclass
class MCPStep:
    """Single step in an MCP chain."""
    name: str
    mcp_type: str  # "library_bridge", "context_builder", "deep_research", etc.
    input_source: str  # "query", "previous_step", "session_context"
    input_key: Optional[str] = None  # Which key from input to use
    timeout_ms: int = 5000
    required: bool = True  # If False, chain continues even if this step fails

@dataclass
class ChainResult:
    """Result of an MCP chain execution."""
    pattern: str
    steps_executed: List[str]
    results: Dict[str, Any]
    session_context: Dict[str, Any]
    total_time_ms: float
    success: bool
    error: Optional[str] = None

class MCPChain:
    """Orchestrates chaining of multiple MCPs."""
    
    def __init__(self):
        self.chains = {
            "knowledge_deep_dive": [
                MCPStep("library_lookup", "library_bridge", "query"),
                MCPStep("context_enrichment", "context_builder", "previous_step", "k_ids"),
                MCPStep("synthesis", "jh_brain", "previous_step", "context"),
            ],
            "research_with_context": [
                MCPStep("local_context", "local_companion", "query"),
                MCPStep("deep_research", "deep_research", "query"),
                MCPStep("merge_results", "context_builder", "previous_step"),
            ],
            "decision_analysis": [
                MCPStep("find_decision", "library_bridge", "query"),
                MCPStep("get_context", "context_builder", "previous_step", "decision_id"),
                MCPStep("analyze", "jh_brain", "previous_step", "context"),
            ],
            "pattern_matching": [
                MCPStep("find_similar", "library_bridge", "query"),
                MCPStep("extract_patterns", "context_builder", "previous_step", "k_ids"),
                MCPStep("apply_patterns", "jh_brain", "previous_step", "patterns"),
            ],
            "generic_with_context": [
                MCPStep("gather_context", "context_builder", "query"),
                MCPStep("enrich_with_library", "library_bridge", "query", required=False),
            ],
        }
    
    def get_chain_for_query(self, query: str, routing_info: Dict) -> Optional[List[MCPStep]]:
        """Get appropriate chain based on query pattern."""
        pattern = routing_info.get("pattern", "generic")
        
        chain_map = {
            "knowledge": "knowledge_deep_dive",
            "decision": "decision_analysis",
            "pattern": "pattern_matching",
            "research": "research_with_context",
            "comparison": "research_with_context",
            "generic": "generic_with_context",
        }
        
        chain_name = chain_map.get(pattern)
        if chain_name and chain_name in self.chains:
            logger.info(f"Selected chain: {chain_name} for pattern: {pattern}")
            return self.chains[chain_name]
        
        return None
    
    async def execute_chain(
        self,
        chain: List[MCPStep],
        query: str,
        session_context: Dict[str, Any],
        available_capabilities: List[str]
    ) -> ChainResult:
        """
        Execute an MCP chain.
        
        Returns: ChainResult with all step outputs and merged context.
        """
        import time
        start_time = time.time()
        
        results = {}
        steps_executed = []
        current_context = session_context.copy()
        
        for step in chain:
            # Check if capability available
            if step.mcp_type not in available_capabilities:
                if step.required:
                    logger.warning(f"Required capability unavailable: {step.mcp_type}")
                    return ChainResult(
                        pattern="chain",
                        steps_executed=steps_executed,
                        results=results,
                        session_context=current_context,
                        total_time_ms=(time.time() - start_time) * 1000,
                        success=False,
                        error=f"Required capability unavailable: {step.mcp_type}"
                    )
                else:
                    logger.info(f"Skipping optional step: {step.name}")
                    continue
            
            # Prepare input for this step
            if step.input_source == "query":
                step_input = query
            elif step.input_source == "previous_step":
                if step.input_key:
                    step_input = results.get(steps_executed[-1], {}).get(step.input_key)
                else:
                    step_input = results.get(steps_executed[-1])
            elif step.input_source == "session_context":
                if step.input_key:
                    step_input = current_context.get(step.input_key)
                else:
                    step_input = current_context
            else:
                step_input = None
            
            # Execute step (simulated for now)
            try:
                step_result = await self._execute_mcp_step(
                    step=step,
                    input_data=step_input,
                    context=current_context
                )
                
                results[step.name] = step_result
                steps_executed.append(step.name)
                
                # Update context with step result
                if isinstance(step_result, dict):
                    current_context.update(step_result)
                
                logger.info(f"Step executed: {step.name}")
                
            except Exception as e:
                logger.error(f"Step failed: {step.name} - {e}")
                if step.required:
                    return ChainResult(
                        pattern="chain",
                        steps_executed=steps_executed,
                        results=results,
                        session_context=current_context,
                        total_time_ms=(time.time() - start_time) * 1000,
                        success=False,
                        error=f"Step failed: {step.name}"
                    )
        
        return ChainResult(
            pattern="chain",
            steps_executed=steps_executed,
            results=results,
            session_context=current_context,
            total_time_ms=(time.time() - start_time) * 1000,
            success=True
        )
    
    async def _execute_mcp_step(
        self,
        step: MCPStep,
        input_data: Any,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single MCP step by calling the actual MCP server."""
        import subprocess
        import json
        import os
        from pathlib import Path
        
        # Workspace-agnostic path resolution
        try:
            from library_accessor import find_workspace_root
            workspace_root = find_workspace_root()
        except Exception as e:
            logger.error(f"Cannot find workspace root: {e}")
            raise RuntimeError("Workspace root not found")
        
        # Map MCP types to their relative server paths
        mcp_servers = {
            "context_builder": "mcp_servers/context-builder/server.js",
            "library_bridge": "mcp_servers/library-bridge/server.js",
            "deep_research": "mcp_servers/deep-research-mcp/server.js",
            "project_planning": "mcp_servers/project-planning/server.js",
        }
        
        relative_path = mcp_servers.get(step.mcp_type)
        if not relative_path:
            raise ValueError(f"Unknown MCP type: {step.mcp_type}")
        
        server_path = os.path.join(workspace_root, relative_path)
        
        if not os.path.exists(server_path):
            logger.error(f"MCP server not found at {server_path}")
            raise RuntimeError(f"MCP server not found: {step.mcp_type}")
        
        try:
            # Call the actual MCP server via subprocess
            proc = subprocess.Popen(
                ["node", server_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Send request to MCP
            request = json.dumps({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": f"{step.mcp_type}_tool",
                    "arguments": {"query": str(input_data) if input_data else ""}
                }
            })
            
            stdout, stderr = proc.communicate(input=request, timeout=step.timeout_ms / 1000)
            
            if proc.returncode != 0:
                logger.error(f"MCP {step.mcp_type} failed: {stderr}")
                raise RuntimeError(f"MCP execution failed: {stderr}")
            
            # Parse MCP response
            response = json.loads(stdout) if stdout else {}
            
            logger.info(f"MCP {step.mcp_type} executed successfully for step: {step.name}")
            
            return {
                "step": step.name,
                "mcp": step.mcp_type,
                "result": response.get("result", {}),
                "confidence": response.get("confidence", 0.7),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except subprocess.TimeoutExpired:
            logger.error(f"MCP {step.mcp_type} timed out")
            raise RuntimeError(f"MCP {step.mcp_type} timed out after {step.timeout_ms}ms")
        except Exception as e:
            logger.error(f"Error executing MCP {step.mcp_type}: {e}")
            raise

# Global chain orchestrator
chain_orchestrator = MCPChain()

async def get_chain_for_query(query: str, routing_info: Dict) -> Optional[List[MCPStep]]:
    """Get appropriate chain for a query."""
    return chain_orchestrator.get_chain_for_query(query, routing_info)

async def execute_mcp_chain(
    chain: List[MCPStep],
    query: str,
    session_context: Dict[str, Any],
    available_capabilities: List[str]
) -> ChainResult:
    """Execute an MCP chain."""
    return await chain_orchestrator.execute_chain(
        chain=chain,
        query=query,
        session_context=session_context,
        available_capabilities=available_capabilities
    )
