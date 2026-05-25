import os
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
import openmeteo_requests
import requests_cache
from retry_requests import retry
from pydantic import BaseModel, Field
from typing import List
from langchain_core.output_parsers import PydanticOutputParser

os.getenv("GROQ_API_KEY")

class Enterpriseenvironment:
    def __init__(self):
        self.inventory = {
            "microchips": {"stock": 400, "threshold": 1000},
            "lithium_batteries": {"stock": 150, "threshold": 500},
            "steel_frames": {"stock": 8000, "threshold": 2000}
        }
        
        # Suppliers mapped to specific items
        self.suppliers = {
            "Shanghai_Tech": {"item": "microchips", "location": "Shanghai", "cost": 10, "lat": 31.23, "lon": 121.47},
            "Rotterdam_Elec": {"item": "microchips", "location": "Rotterdam", "cost": 15, "lat": 51.92, "lon": 4.47},
            "Shenzhen_Power": {"item": "lithium_batteries", "location": "Shenzhen", "cost": 40, "lat": 22.54, "lon": 114.05},
            "Texas_Energy": {"item": "lithium_batteries", "location": "Houston", "cost": 65, "lat": 29.76, "lon": -95.36}
        }
        
        self.rubix_wallet_balance = 100000
        self.transaction_log = []

    def log_transaction(self, supplier, amount):
        if self.rubix_wallet_balance >= amount:
            self.rubix_wallet_balance -= amount
            receipt = f"TXN-SUCCESS: Paid ${amount} to {supplier} via Rubix Smart Contract."
            self.transaction_log.append(receipt)
            return receipt
        return "TXN-FAILED: Insufficient funds."

# initialize
env= Enterpriseenvironment()

@tool
def get_full_inventory() -> str:
    """Returns the complete raw data of all items in the warehouse and their minimum thresholds."""
    return str(env.inventory)

@tool
def check_port_weather(location_name: str)-> str:
    """Checks real-time wind speeds at a global shipping port to predict delays"""
    supplier=None
    for key,data in env.suppliers.items():
        if location_name.lower() in key.lower() or location_name.lower() in data["location"].lower():
            supplier=data
            break
    if not supplier:
        return "Location not found in supplier database."
    
    # openmeteo api call
    cache_session=requests_cache.CachedSession('.cache', expire_after=3600)
    retry_session=retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo=openmeteo_requests.Client(session=retry_session)

    url = "https://api.open-meteo.com/v1/forecast"

    
    params={
        "latitude": supplier['lat'],
        "longitude": supplier["lon"],
        "current": "wind_speed_10m"
    }

    response= openmeteo.weather_api(url, params=params)
    wind_speed= response[0].Current().Variables(0).Value()
    response= openmeteo.weather_api(url, params=params)
    wind_speed= response[0].Current().Variables(0).Value()

    
    if "Shenzhen" in supplier['location']:
        wind_speed = 85.0
    if wind_speed > 30.0:
        return f"CRITICAL: Wind speed at {supplier['location']} is {wind_speed:.2f} km/h. Port operations are suspended. Expect major shipping delays."
    return f"Wind speed at {supplier['location']} is {wind_speed:.2f} km/h. Port operations are normal."

@tool 
def execute_rubix_contract(supplier_id: str, order_quantity: int) -> str:
    """Execute blockchain payment to a supplier."""
    if supplier_id not in env.suppliers:
        return f"Error: Invalid supplier ID {supplier_id}"
    
    #  find item  supplier provides
    item_name = env.suppliers[supplier_id]["item"]
    cost_per_unit = env.suppliers[supplier_id]["cost"]
    total_cost = cost_per_unit * order_quantity
    
    # Update item's stock
    env.inventory[item_name]["stock"] += order_quantity

    receipt = env.log_transaction(supplier_id, total_cost)
    return f"Order placed for {order_quantity} {item_name}s. {receipt}"

class SupplyChainState(TypedDict):
    low_stock_items: list     
    requires_restock: bool
    logistics_data: str
    action_plan: str
    approved_orders: list 
    final_receipts: list

#  llm
llm = ChatOpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1",
    model="llama-3.3-70b-versatile",
    temperature=0
)

def inventory_agent(state: SupplyChainState) -> SupplyChainState:
    print("AGENT 1: INVENTORY MANAGER")
    
    # 1. fetches data
    raw_data = get_full_inventory.invoke({})
    
    # 2. LLM to analyze the raw data
    prompt = f"""
    You are the Autonomous Inventory Manager.
    Here is the live database pull from our ERP system: {raw_data}
    
    Your job is to analyze this data and determine WHICH items are strictly below their threshold.
    
    Respond ONLY with a comma-separated list of the item names that need restocking. 
    If everything is fine, reply with the word 'NONE'.
    """
    
    # processing
    response = llm.invoke([HumanMessage(content=prompt)])
    content = response.content.strip()
    
    print(f"Agent Analysis: {content}\n")
    
    if content == "NONE":
        return {"low_stock_items": [], "requires_restock": False}
    else:
        
        items_to_order = [item.strip() for item in content.split(',')]
        return {"low_stock_items": items_to_order, "requires_restock": True}

def oracle_agent(state: SupplyChainState) -> SupplyChainState:
    print("AGENT 2: LOGISTICS ORACLE")
    items_needed = state['low_stock_items']
    weather_reports = []
    
    # Loop through the database to find suppliers
    for item in items_needed:
        for supp_id, supp_data in env.suppliers.items():
            if supp_data["item"] == item:
                weather = check_port_weather.invoke(supp_data["location"])
                weather_reports.append(f"Supplier: {supp_id} (Provides: {item}, Cost: ${supp_data['cost']}) -> {weather}")
    
    combined_logistics = "\n".join(weather_reports)
    print(f"Weather Log: \n{combined_logistics}\n")
    return {"logistics_data": combined_logistics}


class Order(BaseModel):
    supplier: str = Field(description="The exact ID of the selected supplier (e.g., Shanghai_Tech)")
    qty: int = Field(description="The quantity to order, strictly an integer. Always 1000.")

class ActionPlan(BaseModel):
    explanation: str = Field(description="A brief explanation of why these suppliers were chosen based on weather and cost.")
    orders: List[Order] = Field(description="The list of approved orders for the setter agent.")


def analyst_agent(state: SupplyChainState) -> SupplyChainState:
    print("AGENT 3: RISK ANALYST")
    
    # parser
    parser = PydanticOutputParser(pydantic_object=ActionPlan)
    
    prompt = f"""
    You are a Supply Chain Risk Analyst.
    Items needing restock: {state['low_stock_items']}
    
    Here is the logistics and cost data for all potential suppliers:
    {state['logistics_data']}
    
    For EACH item needing restock, select ONE supplier.
    Rule 1: If a supplier has "CRITICAL" wind speeds (>30km/h), DO NOT use them.
    Rule 2: Out of the remaining safe suppliers, pick the one with the lowest Cost.
    
    {parser.get_format_instructions()}
    """
    
    # LLM invoke
    response = llm.invoke([HumanMessage(content=prompt)])
    
    # the LLM's text output
    try:
        result = parser.parse(response.content)
        print(f"Analyst Reasoning: {result.explanation}\n")
        
        # Extract data
        approved_orders = [{"supplier": order.supplier, "qty": order.qty} for order in result.orders]
        plan_string = "\n".join([f"ORDER -> {order['supplier']}: {order['qty']} units" for order in approved_orders])
        
        return {"action_plan": plan_string, "approved_orders": approved_orders}
        
    except Exception as e:
        print(f"\n PARSING ERROR: {e}")
        print(f"Raw Output was: {response.content}")
        # Fallback
        return {"action_plan": "Error parsing LLM response", "approved_orders": []}
    
def human_approval_node(state: SupplyChainState) -> SupplyChainState:
    
    print("\n============================")
    print(" HUMAN IN THE LOOP REQUIRED ")
    print("==============================")
    print(f"The AI proposes the following actions:\n{state['action_plan']}")
    print(f"Total Rubix Wallet Balance: ${env.rubix_wallet_balance}")
    return state

def route_human_decision(state: SupplyChainState):
    # terminal prompt
    user_input = input("\nDo you approve the execution of these smart contracts? (Y/N): ")
    if user_input.strip().upper() == 'Y':
        print("-> ROUTER: Human Approved. Executing Blockchain Settlement...")
        return "settlement"
    else:
        print("-> ROUTER: Transaction aborted by Human command.")
        return END

def settlement_agent(state: SupplyChainState) -> SupplyChainState:
    print(" AGENT 4: PROCUREMENT SETTLER")
    receipts = []
    
    for order in state['approved_orders']:
        receipt = execute_rubix_contract.invoke({
            "supplier_id": order['supplier'], 
            "order_quantity": order['qty']
        })
        print(f"Blockchain Log: {receipt}")
        receipts.append(receipt)
        
    return {"final_receipts": receipts}
    

def route_inventory(state: SupplyChainState):
    if state.get("requires_restock"):
        print("-> ROUTER: Shortages detected. Waking up Oracle...")
        return "oracle"
    else:
        print("-> ROUTER: Inventory fully stocked. System going to sleep.")
        return END


# initialize graph
workflow = StateGraph(SupplyChainState)

# add agents 
workflow.add_node("inventory", inventory_agent)
workflow.add_node("oracle", oracle_agent)
workflow.add_node("analyst", analyst_agent)
workflow.add_node("human_approval", human_approval_node)
workflow.add_node("settlement", settlement_agent)

# flow
workflow.set_entry_point("inventory")
workflow.add_conditional_edges("inventory", route_inventory, {"oracle": "oracle", END: END})

workflow.add_edge("oracle", "analyst")
workflow.add_edge("analyst", "human_approval")

workflow.add_conditional_edges("human_approval", route_human_decision, {"settlement": "settlement", END: END})
workflow.add_edge("settlement", END)

app = workflow.compile()


if __name__ == "__main__":
    print("INITIATING AUTONOMOUS SUPPLY CHAIN SYSTEM")

    initial_state={
        "inventory_status": "",
        "requires_restock": False,
        "logistics_data": "",
        "selected_supplier": "",
        "action_plan": "",
        "final_receipt": ""
    }

    final_state=app.invoke(initial_state)
    print("SYSTEM EXECUTION COMPLETE")