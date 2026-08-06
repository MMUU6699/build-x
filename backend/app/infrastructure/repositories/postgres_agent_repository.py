import json
import logging
from typing import Optional

from sqlalchemy import update
from datetime import datetime, UTC

from app.domain.models.agent import Agent
from app.domain.models.memory import Memory
from app.domain.repositories.agent_repository import AgentRepository
from app.infrastructure.models.postgres import AgentRow
from app.infrastructure.models.memory_serialization import deserialize_memory, serialize_memory
from app.infrastructure.storage.postgres import get_session_factory

logger = logging.getLogger(__name__)


class PostgresAgentRepository(AgentRepository):
    """PostgreSQL implementation of AgentRepository"""

    async def save(self, agent: Agent) -> None:
        """Save or update an agent"""
        memories = {name: serialize_memory(m) for name, m in agent.memories.items()}
        async with get_session_factory()() as db:
            row = await db.get(AgentRow, agent.id)
            if row is None:
                db.add(AgentRow(
                    agent_id=agent.id,
                    model_name=agent.model_name,
                    temperature=agent.temperature,
                    max_tokens=agent.max_tokens,
                    memories=memories,
                    created_at=agent.created_at,
                    updated_at=agent.updated_at,
                ))
            else:
                row.model_name = agent.model_name
                row.temperature = agent.temperature
                row.max_tokens = agent.max_tokens
                row.memories = memories
                row.updated_at = datetime.now(UTC)
            await db.commit()

    async def find_by_id(self, agent_id: str) -> Optional[Agent]:
        """Find an agent by its ID"""
        async with get_session_factory()() as db:
            row = await db.get(AgentRow, agent_id)
            if not row:
                return None
            return Agent(
                id=row.agent_id,
                model_name=row.model_name,
                temperature=row.temperature,
                max_tokens=row.max_tokens,
                memories={
                    name: deserialize_memory(raw) for name, raw in (row.memories or {}).items()
                },
                created_at=row.created_at,
                updated_at=row.updated_at,
            )

    async def _set_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        async with get_session_factory()() as db:
            row = await db.get(AgentRow, agent_id)
            if not row:
                raise ValueError(f"Agent {agent_id} not found")
            memories = dict(row.memories or {})
            memories[name] = serialize_memory(memory)
            row.memories = memories
            row.updated_at = datetime.now(UTC)
            await db.commit()

    async def add_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        """Add or update a memory for an agent"""
        await self._set_memory(agent_id, name, memory)

    async def get_memory(self, agent_id: str, name: str) -> Memory:
        """Get memory by name from agent, create if not exists"""
        async with get_session_factory()() as db:
            row = await db.get(AgentRow, agent_id)
            if not row:
                raise ValueError(f"Agent {agent_id} not found")
            return deserialize_memory((row.memories or {}).get(name))

    async def save_memory(self, agent_id: str, name: str, memory: Memory) -> None:
        """Update the messages of a memory"""
        await self._set_memory(agent_id, name, memory)
