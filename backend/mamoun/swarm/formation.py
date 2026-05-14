"""
Swarm Formation Agent — الذكاء الجماعي التكويني
v16.0

Based on:
- "Subsumption Pattern Learning (SPL)" — hierarchical multi-agent framework
- "Emergent Collective Memory in Decentralized Multi-Agent AI Systems"
- "Swarm Agentic AI pattern" — AWS Builder

Key Features:
1. Self-organizing teams: Agents form teams around complex goals automatically
2. Team dissolution: Teams disband when the goal is achieved
3. Collective memory: Lessons learned by one swarm are available to all future swarms
4. Dynamic task decomposition: Complex projects split into sub-tasks automatically
5. Skill-based agent assignment: Right agent for right sub-task
"""

import json
import time
import logging
from datetime import datetime, timezone
from typing import Optional
from pathlib import Path
from enum import Enum

logger = logging.getLogger("mamoun.swarm.formation")


class SwarmState(str, Enum):
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETING = "completing"
    DISSOLVED = "dissolved"


class AgentRole(str, Enum):
    COORDINATOR = "coordinator"       # تقسيم المهام وتوزيعها
    RESEARCHER = "researcher"         # بحث وجمع معلومات
    CODER = "coder"                   # كتابة كود
    REVIEWER = "reviewer"             # مراجعة واختبار
    DEPLOYER = "deployer"             # نشر وتثبيت
    ANALYST = "analyst"               # تحليل بيانات
    COMMUNICATOR = "communicator"     # تواصل مع المستخدم


class SwarmAgent:
    """An agent in a swarm."""
    
    def __init__(self, agent_id: str, role: AgentRole, skills: list[str]):
        self.agent_id = agent_id
        self.role = role
        self.skills = skills
        self.current_task: Optional[str] = None
        self.completed_tasks: list[str] = []
    
    def to_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "role": self.role.value,
            "skills": self.skills,
            "current_task": self.current_task,
            "completed_tasks": self.completed_tasks,
        }


class SwarmTask:
    """A task within a swarm."""
    
    def __init__(self, task_id: str, description: str, required_role: AgentRole, parent_id: Optional[str] = None):
        self.task_id = task_id
        self.description = description
        self.required_role = required_role
        self.parent_id = parent_id
        self.status = "pending"  # pending, in_progress, completed, failed
        self.assigned_to: Optional[str] = None
        self.result: Optional[dict] = None
    
    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_role": self.required_role.value,
            "parent_id": self.parent_id,
            "status": self.status,
            "assigned_to": self.assigned_to,
            "result": self.result,
        }


class SwarmFormation:
    """A formed swarm working on a goal."""
    
    def __init__(self, swarm_id: str, goal: str):
        self.swarm_id = swarm_id
        self.goal = goal
        self.state = SwarmState.FORMING
        self.agents: list[SwarmAgent] = []
        self.tasks: list[SwarmTask] = []
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.completed_at: Optional[str] = None
        self.lessons_learned: list[str] = []
    
    def to_dict(self) -> dict:
        return {
            "swarm_id": self.swarm_id,
            "goal": self.goal,
            "state": self.state.value,
            "agents": [a.to_dict() for a in self.agents],
            "tasks": [t.to_dict() for t in self.tasks],
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "lessons_learned": self.lessons_learned,
            "progress": self._calculate_progress(),
        }
    
    def _calculate_progress(self) -> float:
        if not self.tasks:
            return 0.0
        completed = sum(1 for t in self.tasks if t.status == "completed")
        return completed / len(self.tasks)


class CollectiveMemory:
    """Shared memory across all swarms — the 'hive mind'."""
    
    def __init__(self, data_dir: str = "backend/data/swarm"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.memory_path = self.data_dir / "collective_memory.jsonl"
        self.lessons: list[dict] = self._load_lessons()
    
    def _load_lessons(self) -> list:
        lessons = []
        if self.memory_path.exists():
            with open(self.memory_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            lessons.append(json.loads(line))
                        except Exception:
                            continue
        return lessons
    
    def add_lesson(self, lesson: str, swarm_id: str, domain: str, success: bool):
        entry = {
            "lesson": lesson,
            "swarm_id": swarm_id,
            "domain": domain,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.lessons.append(entry)
        with open(self.memory_path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_relevant_lessons(self, domain: str, limit: int = 5) -> list[dict]:
        relevant = [l for l in self.lessons if l.get("domain") == domain]
        relevant.sort(key=lambda l: l.get("timestamp", ""), reverse=True)
        return relevant[:limit]


class SwarmFormationAgent:
    """
    The Swarm Formation Agent — creates and manages swarms of agents.
    """
    
    def __init__(self, data_dir: str = "backend/data/swarm"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.swarms_path = self.data_dir / "swarms.jsonl"
        self.collective_memory = CollectiveMemory(data_dir)
        self.active_swarms: list[SwarmFormation] = []
        self.completed_swarms: list[SwarmFormation] = []
    
    def form_swarm(self, goal: str, available_agents: list[dict]) -> SwarmFormation:
        """
        Form a new swarm to achieve a goal.
        Automatically decomposes the goal into tasks and assigns agents.
        """
        swarm_id = f"swarm_{int(time.time())}"
        swarm = SwarmFormation(swarm_id=swarm_id, goal=goal)
        
        # Decompose goal into tasks
        tasks = self._decompose_goal(goal)
        swarm.tasks = tasks
        
        # Assign agents to tasks based on skills
        for task in swarm.tasks:
            best_agent = self._find_best_agent(task, available_agents)
            if best_agent:
                agent = SwarmAgent(
                    agent_id=best_agent["id"],
                    role=task.required_role,
                    skills=best_agent.get("skills", []),
                )
                agent.current_task = task.task_id
                task.assigned_to = agent.agent_id
                task.status = "in_progress"
                if not any(a.agent_id == agent.agent_id for a in swarm.agents):
                    swarm.agents.append(agent)
        
        swarm.state = SwarmState.ACTIVE
        self.active_swarms.append(swarm)
        
        # Save
        with open(self.swarms_path, "a") as f:
            f.write(json.dumps(swarm.to_dict(), ensure_ascii=False) + "\n")
        
        logger.info("Swarm formed: %s with %d agents for goal: %s", swarm_id, len(swarm.agents), goal)
        return swarm
    
    def _decompose_goal(self, goal: str) -> list[SwarmTask]:
        """
        Decompose a complex goal into sub-tasks.
        Uses heuristic-based decomposition (in production, this would use LLM).
        """
        tasks = []
        base_id = f"t_{int(time.time())}"
        
        # Standard project decomposition pattern
        task_patterns = [
            ("بحث وتحليل المتطلبات", AgentRole.RESEARCHER),
            ("تخطيط البنية التقنية", AgentRole.COORDINATOR),
            ("تطوير الكود الأساسي", AgentRole.CODER),
            ("مراجعة واختبار", AgentRole.REVIEWER),
            ("نشر وتثبيت", AgentRole.DEPLOYER),
        ]
        
        for i, (desc, role) in enumerate(task_patterns):
            task = SwarmTask(
                task_id=f"{base_id}_{i}",
                description=desc,
                required_role=role,
                parent_id=f"{base_id}_{i-1}" if i > 0 else None,
            )
            tasks.append(task)
        
        return tasks
    
    def _find_best_agent(self, task: SwarmTask, available_agents: list[dict]) -> Optional[dict]:
        """Find the best agent for a task based on role and skills."""
        best = None
        best_score = -1
        
        for agent in available_agents:
            score = 0
            role_match = agent.get("role", "") == task.required_role.value
            if role_match:
                score += 10
            
            # Skill matching
            agent_skills = set(agent.get("skills", []))
            required_skills = set(task.description.split())
            overlap = agent_skills & required_skills
            score += len(overlap)
            
            if score > best_score:
                best = agent
                best_score = score
        
        return best
    
    def complete_swarm(self, swarm_id: str, lessons: list[str]) -> bool:
        """Complete a swarm and dissolve it."""
        for swarm in self.active_swarms:
            if swarm.swarm_id == swarm_id:
                swarm.state = SwarmState.DISSOLVED
                swarm.completed_at = datetime.now(timezone.utc).isoformat()
                swarm.lessons_learned = lessons
                
                # Add lessons to collective memory
                for lesson in lessons:
                    self.collective_memory.add_lesson(
                        lesson=lesson,
                        swarm_id=swarm_id,
                        domain="general",
                        success=True,
                    )
                
                self.active_swarms.remove(swarm)
                self.completed_swarms.append(swarm)
                return True
        return False
    
    def get_status(self) -> dict:
        return {
            "active_swarms": len(self.active_swarms),
            "completed_swarms": len(self.completed_swarms),
            "collective_lessons": len(self.collective_memory.lessons),
            "active_swarm_goals": [s.goal for s in self.active_swarms],
        }
