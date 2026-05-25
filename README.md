# Autonomous Agentic Supply Chain System

An enterprise-grade, multi-agent AI supply chain simulator powered by **Groq (Llama-3)** and **LangGraph**. This system demonstrates how an autonomous swarm of AI agents can monitor internal inventory, analyze real-world physical constraints (global weather data), execute rigid financial logic, and trigger decentralized smart-contract settlements with a Human-In-The-Loop (HITL) failsafe.

---

#  Architecture Overview

This project shifts from a traditional linear automation pipeline to a dynamic **Multi-Agent Swarm** utilizing four distinct agentic nodes:

##  1. The Inventory Monitor
Reads internal ERP data to dynamically identify stock shortages across thousands of potential items.

##  2. The Logistics Oracle
Bridges the AI to the physical world by querying the Open-Meteo API to check real-time port weather conditions for global suppliers.

##  3. The Risk Analyst
Utilizes **Llama-3.3-70B** and strict **Pydantic Structured Outputs** to evaluate the Oracle's weather data and supplier costs.

The agent autonomously:
- avoids risky shipping routes
- selects optimal suppliers
- minimizes procurement costs
- pivots to backup suppliers during severe weather disruptions

##  4. The Procurement Settler
Executes mock decentralized financial (DeFi) settlements using a simulated **Rubix Trust Layer** WASM smart contract.

---

#  Enterprise Features

###  Deterministic Logic
Orchestrated using **LangGraph StateGraph** to ensure strict, auditable execution paths.

###  Structured Outputs
Eliminates fragile string parsing by enforcing **Pydantic schemas** on LLM outputs.

###  Human-In-The-Loop (HITL)
The workflow intentionally pauses before financial settlement, allowing a human operator to approve or reject AI-generated procurement actions.

###  External Intelligence Integration
Real-time weather intelligence is integrated directly into supplier selection and logistics risk analysis.

###  Multi-Agent Orchestration
Each AI agent has an isolated responsibility, enabling modular enterprise-scale workflow design.

###  Smart Contract Simulation
Demonstrates decentralized procurement settlement concepts using a simulated blockchain trust layer.

---

#  Tech Stack

| Category | Technologies |
|---|---|
| LLM Orchestration | LangGraph |
| Language Model | Groq API (Llama-3.3-70B) |
| AI Framework | LangChain |
| Structured Validation | Pydantic |
| Backend | Python |
| Weather Intelligence | Open-Meteo API |
| State Management | TypedDict |
| UI Dashboard | Streamlit |
| Workflow Architecture | Multi-Agent DAG |

---

#  Workflow Execution

```text
Inventory Monitor
        ↓
Logistics Oracle
        ↓
Risk Analyst
        ↓
Human Approval Gateway
        ↓
Procurement Settler