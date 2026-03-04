"""
Test for Agent Feedback Flow with IPFS Pin
Submits feedback from a client to an existing agent and verifies data integrity.

Flow:
1. Load existing agent by ID
2. Client submits multiple feedback entries
3. Verify feedback data consistency (value, tags, mcpTool, a2aSkills)
4. Wait for blockchain finalization
5. Verify feedback can be retrieved (if SDK supports it)

Usage:
    Update AGENT_ID constant below to point to your existing agent
"""

import logging
import time
import random
import sys
import os
import pytest

# Configure logging: root logger at WARNING to suppress noisy dependencies
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[logging.StreamHandler(sys.stdout)]
)

# Set debug level ONLY for agent0_sdk
logging.getLogger('agent0_sdk').setLevel(logging.DEBUG)
logging.getLogger('agent0_sdk.core').setLevel(logging.DEBUG)

from agent0_sdk import SDK
from tests.config import (
    CHAIN_ID,
    RPC_URL,
    AGENT_PRIVATE_KEY,
    PINATA_JWT,
    SUBGRAPH_URL,
    AGENT_ID,
    CLIENT_PRIVATE_KEY,
    print_config,
)

# Client configuration (different wallet)
# CLIENT_PRIVATE_KEY is now loaded from config.py (which reads from .env file)
RUN_LIVE_TESTS = os.getenv("RUN_LIVE_TESTS", "0") != "0"


def generateFeedbackData(index: int):
    """Generate random feedback data."""
    scores = [50, 75, 80, 85, 90, 95]
    tags_sets = [
        ["data_analysis", "enterprise"],
        ["code_generation", "enterprise"],
        ["natural_language_understanding", "enterprise"],
        ["problem_solving", "enterprise"],
        ["communication", "enterprise"],
    ]
    
    mcp_tools = [
        "data_analysis",
        "code_generation",
        "natural_language_understanding",
        "problem_solving",
        "communication",
    ]
    skills = [
        "python",
        "javascript",
        "machine_learning",
        "web_development",
        "cloud_computing",
    ]
    return {
        "value": random.choice(scores),
        "tags": random.choice(tags_sets),
        "mcpTool": random.choice(mcp_tools),
        "a2aSkills": [random.choice(skills)],
        "a2aContextId": "enterprise",
    }


def main():
    print("🧪 Testing Agent Feedback Flow with IPFS Pin")
    print_config()
    print("=" * 60)
    
    # SDK Configuration
    sdkConfig_pinata = {
        'chainId': CHAIN_ID,
        'rpcUrl': RPC_URL,
        'ipfs': 'pinata',
        'pinataJwt': PINATA_JWT
        # Subgraph URL auto-defaults from DEFAULT_SUBGRAPH_URLS
    }
    
    # Step 1: Load existing agent
    print("\n📍 Step 1: Load Existing Agent")
    print("-" * 60)
    print(f"Loading agent: {AGENT_ID}")
    
    agentSdk = SDK(**sdkConfig_pinata)  # Read-only for loading
    
    try:
        agent = agentSdk.loadAgent(AGENT_ID)
        print(f"✅ Agent loaded: {agent.name}")
        print(f"   Description: {agent.description[:50]}...")
        print(f"   MCP Endpoint: {agent.mcpEndpoint}")
        print(f"   A2A Endpoint: {agent.a2aEndpoint}")
        print(f"   ENS Endpoint: {agent.ensEndpoint}")
    except Exception as e:
        print(f"❌ Failed to load agent: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Step 2: Client submits feedback (no pre-authorization needed)
    print("\n📍 Step 2: Client Submits Feedback")
    print("-" * 60)
    
    clientSdk = SDK(signer=CLIENT_PRIVATE_KEY, **sdkConfig_pinata)
    clientAddress = clientSdk.web3_client.account.address
    print(f"Client address: {clientAddress}")
    print("Note: Feedback no longer requires pre-authorization (feedbackAuth removed)")
    
    # Agent SDK for responses
    agentSdkWithSigner = SDK(signer=AGENT_PRIVATE_KEY, **sdkConfig_pinata)
    
    # Step 3: Client submits feedback
    print("\n📍 Step 3: Client Submits Feedback")
    print("-" * 60)
    
    feedbackEntries = []
    numFeedback = 1

    # On-chain-only feedback (explicitly no file upload)
    print("\n  Submitting on-chain-only feedback (no feedbackFile):")
    onchain_tx = clientSdk.giveFeedback(
        agentId=AGENT_ID,
        value=1,
        tag1="onchain",
        tag2="only",
        endpoint="https://example.com/onchain-only",
        feedbackFile=None,
    )
    onchain_only = onchain_tx.wait_confirmed(timeout=120).result
    if onchain_only.fileURI:
        raise AssertionError(
            f"Expected on-chain-only feedback to have no fileURI, got: {onchain_only.fileURI}"
        )
    
    for i in range(numFeedback):
        print(f"\n  Submitting Feedback #{i+1}:")
        feedbackData = generateFeedbackData(i+1)
        
        # Prepare off-chain feedback file (optional rich data)
        feedbackFile = clientSdk.prepareFeedbackFile({
            "mcpTool": feedbackData.get("mcpTool"),
            "a2aSkills": feedbackData.get("a2aSkills"),
            "a2aContextId": feedbackData.get("a2aContextId"),
            "text": feedbackData.get("text"),
        })

        tags = feedbackData.get("tags") or []
        tag1 = tags[0] if len(tags) > 0 else None
        tag2 = tags[1] if len(tags) > 1 else None
        
        print(f"  - Value: {feedbackData['value']}")
        print(f"  - Tags: {feedbackData['tags']}")
        print(f"  - mcpTool: {feedbackData.get('mcpTool')}")
        print(f"  - a2aSkills: {feedbackData.get('a2aSkills')}")
        
        # Submit feedback
        try:
            tx = clientSdk.giveFeedback(
                agentId=AGENT_ID,
                value=feedbackData["value"],
                tag1=tag1,
                tag2=tag2,
                endpoint=feedbackData.get("endpoint"),
                feedbackFile=feedbackFile,
            )
            feedback = tx.wait_confirmed(timeout=180).result
            
            # Extract actual feedback index from the returned Feedback object
            # feedback.id is a tuple: (agentId, clientAddress, feedbackIndex)
            actualFeedbackIndex = feedback.id[2]
            
            feedbackEntries.append({
                'index': actualFeedbackIndex,  # Use actual index from blockchain
                'data': feedbackData,
                'feedback': feedback
            })
            
            print(f"  ✅ Feedback #{actualFeedbackIndex} submitted successfully (entry #{i+1} in this test)")
            if feedback.fileURI:
                print(f"     File URI: {feedback.fileURI}")
            
        except Exception as e:
            print(f"  ❌ Failed to submit feedback #{i+1}: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        time.sleep(2)  # Wait between submissions
    
    # Step 4: Agent (Server) Responds to Feedback
    print("\n📍 Step 4: Agent (Server) Responds to Feedback")
    print("-" * 60)
    
    clientAddress = clientSdk.web3_client.account.address
    
    for i, entry in enumerate(feedbackEntries):
        # Use the actual feedback index that was returned when submitting
        feedbackIndex = entry['index']
        print(f"\n  Responding to Feedback #{feedbackIndex}:")
        
        # Generate response data
        responseData = {
            'text': f"Thank you for your feedback! We appreciate your input.",
            'timestamp': int(time.time()),
            'responder': 'agent'
        }
        
        try:
            # Agent responds to the client's feedback
            resp_tx = agentSdkWithSigner.appendResponse(
                agentId=AGENT_ID,
                clientAddress=clientAddress,
                feedbackIndex=feedbackIndex,
                response=responseData
            )
            updatedFeedback = resp_tx.wait_confirmed(timeout=180).result
            
            print(f"  ✅ Response submitted to feedback #{feedbackIndex}")
            entry['response'] = responseData
            entry['updatedFeedback'] = updatedFeedback
        except Exception as e:
            print(f"  ❌ Failed to submit response: {e}")
        
        time.sleep(2)  # Wait between responses
    
    # Step 5: Wait for blockchain finalization
    print("\n📍 Step 5: Waiting for Blockchain Finalization")
    print("-" * 60)
    print("⏳ Waiting 15 seconds for blockchain to finalize...")
    time.sleep(15)
    
    # Step 6: Verify feedback data and responses
    print("\n📍 Step 6: Verify Feedback Data Integrity")
    print("-" * 60)
    
    allMatch = True
    
    for i, entry in enumerate(feedbackEntries, 1):
        print(f"\n  Feedback #{i}:")
        data = entry['data']
        feedback = entry['feedback']
        
        # Verify feedback object fields (spec-aligned: mcpTool, a2aSkills)
        expected_skills = data.get("a2aSkills") or []
        if not isinstance(expected_skills, list):
            expected_skills = [expected_skills] if expected_skills else []
        checks = [
            ("Value", data["value"], feedback.value),
            ("Tags", data["tags"], feedback.tags),
            ("mcpTool", data.get("mcpTool"), feedback.mcpTool),
            ("a2aSkills", expected_skills, feedback.a2aSkills or []),
        ]
        
        for field_name, expected, actual in checks:
            if expected == actual:
                print(f"    ✅ {field_name}: {actual}")
            else:
                print(f"    ❌ {field_name}: expected={expected}, got={actual}")
                allMatch = False
        
        # Verify file URI exists
        if feedback.fileURI:
            print(f"    ✅ File URI: {feedback.fileURI}")
        else:
            print(f"    ⚠️  No file URI (IPFS storage may have failed)")
        
        # Verify server response was added
        if 'response' in entry and entry.get('updatedFeedback'):
            print(f"    ✅ Server Response: Recorded successfully")
    
    # Step 7: Wait for subgraph indexing
    print("\n📍 Step 7: Waiting for Subgraph to Index")
    print("-" * 60)
    print("⏳ Waiting 60 seconds for subgraph to catch up with blockchain events...")
    print("   (Subgraphs can take up to a minute to index new blocks)")
    time.sleep(60)
    
    # Step 8: Test getFeedback (direct access)
    print("\n📍 Step 8: Test getFeedback (Direct Access)")
    print("-" * 60)
    
    for i, entry in enumerate(feedbackEntries):
        # Use the actual feedback index that was returned when submitting
        feedbackIndex = entry['index']
        print(f"\n  Fetching Feedback #{feedbackIndex} using getFeedback():")
        
        try:
            # Use agentSdkWithSigner since agentSdk has no subgraph_client
            retrievedFeedback = agentSdkWithSigner.getFeedback(
                agentId=AGENT_ID,
                clientAddress=clientAddress,
                feedbackIndex=feedbackIndex
            )
            
            print(f"    ✅ Retrieved feedback successfully")
            print(f"    - Value: {retrievedFeedback.value}")
            print(f"    - Tags: {retrievedFeedback.tags}")
            print(f"    - mcpTool: {retrievedFeedback.mcpTool}")
            print(f"    - a2aSkills: {retrievedFeedback.a2aSkills}")
            print(f"    - Is Revoked: {retrievedFeedback.isRevoked}")
            print(f"    - Has Responses: {len(retrievedFeedback.answers)} response(s)")
            if retrievedFeedback.fileURI:
                print(f"    - File URI: {retrievedFeedback.fileURI}")
            
            # Verify retrieved feedback matches original
            expected = entry["data"]
            if (
                retrievedFeedback.value == expected["value"]
                and retrievedFeedback.mcpTool == expected.get("mcpTool")
                and (retrievedFeedback.a2aSkills or []) == (expected.get("a2aSkills") or [])
            ):
                print(f"    ✅ Retrieved feedback matches original submission")
            else:
                print(f"    ❌ Retrieved feedback does not match original")
                allMatch = False
                
        except Exception as e:
            print(f"    ❌ Failed to retrieve feedback: {e}")
            allMatch = False
    
    # Step 9: Test searchFeedback (with filters)
    print("\n📍 Step 9: Test searchFeedback (With Filters)")
    print("-" * 60)
    
    # Test 1: Search by mcpTool (filter param still named capabilities)
    print("\n  Test 1: Search feedback by mcpTool (capabilities filter)")
    test_mcp_tool = feedbackEntries[0]["data"].get("mcpTool")
    if test_mcp_tool:
        try:
            results = agentSdkWithSigner.searchFeedback(
                agentId=AGENT_ID,
                capabilities=[test_mcp_tool],
                first=10,
                skip=0,
            )
            print(f"    ✅ Found {len(results)} feedback entry/entries with mcpTool '{test_mcp_tool}'")
            if results:
                for fb in results:
                    print(f"      - Value: {fb.value}, Tags: {fb.tags}")
        except Exception as e:
            print(f"    ❌ Failed to search feedback by mcpTool: {e}")
            allMatch = False

    # Test 2: Search by a2aSkills (filter param still named skills)
    print("\n  Test 2: Search feedback by a2aSkills (skills filter)")
    test_skills = feedbackEntries[0]["data"].get("a2aSkills") or []
    test_skill = test_skills[0] if test_skills else None
    if test_skill:
        try:
            results = agentSdkWithSigner.searchFeedback(
                agentId=AGENT_ID,
                skills=[test_skill],
                first=10,
                skip=0,
            )
            print(f"    ✅ Found {len(results)} feedback entry/entries with skill '{test_skill}'")
            if results:
                for fb in results:
                    print(f"      - Value: {fb.value}, Tags: {fb.tags}")
        except Exception as e:
            print(f"    ❌ Failed to search feedback by skill: {e}")
            allMatch = False

    # Test 3: Search by tags
    print("\n  Test 3: Search feedback by tags")
    testTags = feedbackEntries[0]['data']['tags']
    try:
        results = agentSdkWithSigner.searchFeedback(
            agentId=AGENT_ID,
            tags=testTags,
            first=10,
            skip=0
        )
        print(f"    ✅ Found {len(results)} feedback entry/entries with tags {testTags}")
        if results:
            for fb in results:
                print(f"      - Value: {fb.value}, mcpTool: {fb.mcpTool}")
    except Exception as e:
        print(f"    ❌ Failed to search feedback by tags: {e}")
        allMatch = False
    
    # Test 4: Search by value range
    print("\n  Test 4: Search feedback by value range (75-95)")
    try:
        results = agentSdkWithSigner.searchFeedback(
            agentId=AGENT_ID,
            minValue=75,
            maxValue=95,
            first=10,
            skip=0
        )
        print(f"    ✅ Found {len(results)} feedback entry/entries with value between 75-95")
        if results:
            values = sorted([fb.value for fb in results if fb.value is not None])
            print(f"      - Values found: {values}")
    except Exception as e:
        print(f"    ❌ Failed to search feedback by value range: {e}")
        allMatch = False

    # 1.4.0 additions: reviewer-only and multi-agent search, and empty-filter rejection
    print("\n  Test 5 (1.4.0): reviewer-only search (no agentId)")
    try:
        reviewer_results = agentSdkWithSigner.searchFeedback(
            reviewers=[clientAddress],
            first=10,
            skip=0
        )
        print(f"    ✅ Found {len(reviewer_results)} feedback entry/entries for reviewer {clientAddress}")
        if len(reviewer_results) == 0:
            allMatch = False
    except Exception as e:
        print(f"    ❌ Failed reviewer-only search: {e}")
        allMatch = False

    print("\n  Test 6 (1.4.0): multi-agent search (agents=[])")
    try:
        other_agent_id = None
        try:
            results = agentSdk.searchAgents()
            for item in results[:5]:
                candidate = item.get("agentId") if isinstance(item, dict) else getattr(item, "agentId", None)
                if candidate and candidate != AGENT_ID:
                    other_agent_id = candidate
                    break
        except Exception:
            other_agent_id = None

        agents = [AGENT_ID] + ([other_agent_id] if other_agent_id else [])
        multi_results = agentSdkWithSigner.searchFeedback(
            agents=agents,
            first=10,
            skip=0
        )
        print(f"    ✅ Found {len(multi_results)} feedback entry/entries across agents={agents}")
    except Exception as e:
        print(f"    ❌ Failed multi-agent search: {e}")
        allMatch = False

    print("\n  Test 7 (1.4.0): empty searches are rejected")
    try:
        agentSdkWithSigner.searchFeedback()
        print("    ❌ Expected empty search to raise, but it succeeded")
        allMatch = False
    except ValueError:
        print("    ✅ Empty search correctly rejected")
    except Exception as e:
        print(f"    ❌ Empty search rejected with unexpected error type: {e}")
        allMatch = False
    
    # Final results
    print("\n" + "=" * 60)
    if allMatch:
        print("✅ ALL CHECKS PASSED")
        print("\nSummary:")
        print(f"- Agent ID: {AGENT_ID}")
        print(f"- Agent Name: {agent.name}")
        print(f"- Client address: {clientAddress}")
        print(f"- Feedback entries submitted: {len(feedbackEntries)}")
        print("✅ Feedback flow test complete!")
    else:
        print("❌ SOME CHECKS FAILED")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise


@pytest.mark.integration
def test_feedback_flow_live():
    if not RUN_LIVE_TESTS:
        pytest.skip("Set RUN_LIVE_TESTS=1 to enable live integration tests")
    if not RPC_URL or not RPC_URL.strip():
        pytest.skip("RPC_URL not set")
    if not SUBGRAPH_URL or not SUBGRAPH_URL.strip():
        pytest.skip("SUBGRAPH_URL not set")
    if not AGENT_PRIVATE_KEY or not AGENT_PRIVATE_KEY.strip():
        pytest.skip("AGENT_PRIVATE_KEY not set")
    if not CLIENT_PRIVATE_KEY or not CLIENT_PRIVATE_KEY.strip():
        pytest.skip("CLIENT_PRIVATE_KEY not set")
    if not PINATA_JWT or not PINATA_JWT.strip():
        pytest.skip("PINATA_JWT not set")
    if not AGENT_ID or not AGENT_ID.strip():
        pytest.skip("AGENT_ID not set")

    main()
