import streamlit as st
from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import PydanticOutputParser

#import the environment, tools, LLM, schemas 
from supply_chain_demo import (
    env, 
    llm, 
    get_full_inventory, 
    check_port_weather, 
    execute_rubix_contract, 
    ActionPlan
)

st.set_page_config(page_title=" Agentic Supply Chain", page_icon="🌐", layout="wide")
st.title(" Autonomous Multi-Agent Supply Chain")
st.markdown("Powered by **Groq Llama-3**, **LangGraph**, and the ** Trust Layer**.")

# SIDEBAR
with st.sidebar:
    st.header(" Enterprise ERP")
    st.metric(label=" Wallet Balance", value=f"${env.rubix_wallet_balance:,}")
    st.divider()
    st.subheader("Live Inventory")
    for item, data in env.inventory.items():
        color = "red" if data["stock"] < data["threshold"] else "green"
        st.markdown(f"**{item.replace('_', ' ').title()}**: :{color}[{data['stock']} / {data['threshold']}]")

# State management
if "plan_ready" not in st.session_state:
    st.session_state.plan_ready = False
if "agent_state" not in st.session_state:
    st.session_state.agent_state = {
        "low_stock_items": [], 
        "requires_restock": False, 
        "logistics_data": "", 
        "action_plan": "", 
        "approved_orders": [],
        "agent_1_log": "",      
        "agent_3_reason": ""    
    }

# BUTTON 1
if st.button(" Run Autonomous Supply Chain Scan", use_container_width=True, type="primary"):
    st.session_state.plan_ready = False
    col1, col2, col3 = st.columns(3)
    
    with col1:
        with st.status(" Agent 1: Inventory Monitor", expanded=True) as status:
            raw_data = get_full_inventory.invoke({})
            prompt = f"Analyze this data and determine WHICH items are strictly below their threshold. Respond ONLY with a comma-separated list of items, or 'NONE': {raw_data}"
            res = llm.invoke([HumanMessage(content=prompt)]).content.strip()
            
            if res == "NONE":
                st.success("All inventory levels are healthy.")
                st.session_state.agent_state["requires_restock"] = False
                st.session_state.agent_state["agent_1_log"] = "No shortages detected."
            else:
                items = [i.strip() for i in res.split(',')]
                st.session_state.agent_state["low_stock_items"] = items
                st.session_state.agent_state["requires_restock"] = True
                st.session_state.agent_state["agent_1_log"] = f"Shortages detected: {', '.join(items)}"
                st.warning(st.session_state.agent_state["agent_1_log"])

    if st.session_state.agent_state["requires_restock"]:
        with col2:
            with st.status(" Agent 2: Logistics Oracle", expanded=True) as status:
                weather_logs = []
                for item in st.session_state.agent_state["low_stock_items"]:
                    for supp_id, supp_data in env.suppliers.items():
                        if supp_data["item"] == item:
                            w = check_port_weather.invoke(supp_data["location"])
                            weather_logs.append(f"**{supp_id}** (${supp_data['cost']}): {w}")
                            st.write(f"Checked {supp_data['location']}...")
                
                combined_weather = "\n".join(weather_logs)
                st.session_state.agent_state["logistics_data"] = combined_weather
                status.update(label="Global Weather Fetched", state="complete")
        
        with col3:
            with st.status(" Agent 3: Risk Analyst", expanded=True) as status:
                parser = PydanticOutputParser(pydantic_object=ActionPlan)
                prompt = f"""
                Items needing restock: {st.session_state.agent_state['low_stock_items']}
                Logistics data: {st.session_state.agent_state['logistics_data']}
                For EACH item, select ONE supplier. DO NOT use suppliers with CRITICAL wind (>30km/h). 
                Pick the cheapest safe option. {parser.get_format_instructions()}
                """
                response = parser.parse(llm.invoke([HumanMessage(content=prompt)]).content)
                
                # Save the reasoning to state
                st.session_state.agent_state["agent_3_reason"] = response.explanation
                st.info(f"**Reasoning:** {response.explanation}")
                
                approved_orders = [{"supplier": o.supplier, "qty": o.qty} for o in response.orders]
                plan_str = "\n".join([f"ORDER -> {o['supplier']}: {o['qty']} units" for o in approved_orders])
                
                st.session_state.agent_state["action_plan"] = plan_str
                st.session_state.agent_state["approved_orders"] = approved_orders
                status.update(label="Risk Analyzed", state="complete")
                st.session_state.plan_ready = True

st.divider()

#HUMAN IN LOOP 
if st.session_state.plan_ready:
    st.subheader(" Human Approval Required")
    
    #  visual  trace
    with st.expander(" View AI Swarm Reasoning Trace", expanded=True):
        st.markdown("### Agent 1: Inventory Monitor")
        st.write(st.session_state.agent_state['agent_1_log'])
        
        st.markdown("### Agent 2: Logistics Oracle")
        st.markdown(st.session_state.agent_state['logistics_data'].replace('\n', '\n\n'))
        
        st.markdown("### Agent 3: Risk Analyst")
        st.info(st.session_state.agent_state['agent_3_reason'])

    st.markdown("---")
    st.markdown(f"**The AI Risk Analyst proposes the following action plan:**\n\n{st.session_state.agent_state['action_plan']}")
    
    if st.button("Approve & Execute Smart Contracts", type="primary"):
        with st.status("⛓️ Agent 4: Procurement Settler", expanded=True) as status:
            for order in st.session_state.agent_state['approved_orders']:
                receipt = execute_rubix_contract.invoke({"supplier_id": order['supplier'], "order_quantity": order['qty']})
                st.code(receipt, language="log")
            
            status.update(label="Blockchain Settlement Complete", state="complete")
            st.session_state.plan_ready = False
            st.balloons()