"""
PROMPT 8: Overfitting & Generalization Analysis

Analyzes signal distribution across user archetypes to detect overfitting
and validate generalization.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turn_instrumentation import instrument_user_turn
from conversation_mediator import ShadowConversationMediator
from PROMPT8_USER_ARCHETYPES import CASUAL_USER_TURNS, TASK_ORIENTED_USER_TURNS, EXPLORATORY_USER_TURNS, ALL_ARCHETYPE_TURNS
from collections import Counter


def analyze_archetype(archetype_name, turns):
    """
    Analyze signal distribution for a specific user archetype.
    """
    results = []
    mediator = ShadowConversationMediator()
    
    for turn in turns:
        user_message = turn["user_message"]
        
        # Run instrumentation
        metadata = instrument_user_turn(query=user_message)
        
        # Run shadow mediator
        decision = mediator.compute_decision(
            query=user_message,
            recent_turns=[],
            query_metadata=metadata
        )
        
        results.append({
            "turn_index": turn["turn_index"],
            "message_length": turn["message_length"],
            "signals": {
                "query_type": metadata["query_type"],
                "depth_requested": metadata["depth_requested"],
                "alignment_signal": metadata["alignment_signal"],
                "tools_requested": metadata["tools_requested"],
            },
            "mediator": {
                "verbosity": decision.verbosity,
                "structure": decision.structure,
                "show_reasoning": decision.show_reasoning,
                "ask_clarifying_question": decision.ask_clarifying_question,
                "confidence": decision.confidence,
            }
        })
    
    # Compute distributions
    signal_freq = {
        "depth_requested": sum(1 for r in results if r["signals"]["depth_requested"]) / len(results),
        "alignment_signal": sum(1 for r in results if r["signals"]["alignment_signal"]) / len(results),
        "tools_requested": sum(1 for r in results if r["signals"]["tools_requested"]) / len(results),
    }
    
    query_type_dist = Counter(r["signals"]["query_type"] for r in results)
    query_type_freq = {k: v/len(results) for k, v in query_type_dist.items()}
    
    verbosity_dist = Counter(r["mediator"]["verbosity"] for r in results)
    verbosity_freq = {k: v/len(results) for k, v in verbosity_dist.items()}
    
    structure_dist = Counter(r["mediator"]["structure"] for r in results)
    structure_freq = {k: v/len(results) for k, v in structure_dist.items()}
    
    mediator_freq = {
        "show_reasoning": sum(1 for r in results if r["mediator"]["show_reasoning"]) / len(results),
        "ask_clarifying_question": sum(1 for r in results if r["mediator"]["ask_clarifying_question"]) / len(results),
    }
    
    avg_confidence = sum(r["mediator"]["confidence"] for r in results) / len(results)
    avg_message_length = sum(r["message_length"] for r in results) / len(results)
    
    return {
        "archetype": archetype_name,
        "sample_size": len(results),
        "avg_message_length": avg_message_length,
        "signal_frequency": signal_freq,
        "query_type_distribution": query_type_freq,
        "verbosity_distribution": verbosity_freq,
        "structure_distribution": structure_freq,
        "mediator_frequency": mediator_freq,
        "avg_confidence": avg_confidence,
        "results": results,
    }


def detect_bias(archetype_stats):
    """
    Detect potential biases in signal detection.
    """
    biases = []
    
    # Check message length correlation with depth_requested
    for stats in archetype_stats:
        archetype = stats["archetype"]
        avg_length = stats["avg_message_length"]
        depth_freq = stats["signal_frequency"]["depth_requested"]
        
        # Bias: depth_requested correlates too strongly with long messages
        if avg_length > 60 and depth_freq > 0.5:
            biases.append({
                "type": "length_bias",
                "archetype": archetype,
                "description": f"{archetype} has avg message length {avg_length:.0f} chars and {depth_freq:.1%} depth requests",
                "risk": "moderate",
                "recommendation": "Depth detection may be biased toward verbose users"
            })
        elif avg_length < 40 and depth_freq < 0.1:
            biases.append({
                "type": "length_bias",
                "archetype": archetype,
                "description": f"{archetype} has avg message length {avg_length:.0f} chars and only {depth_freq:.1%} depth requests",
                "risk": "low",
                "recommendation": "Casual users may not trigger depth detection even when needed"
            })
    
    # Check verbosity bias toward exploratory users
    exploratory_stats = next(s for s in archetype_stats if s["archetype"] == "exploratory")
    casual_stats = next(s for s in archetype_stats if s["archetype"] == "casual")
    
    exploratory_high_verbosity = exploratory_stats["verbosity_distribution"].get("high", 0)
    casual_high_verbosity = casual_stats["verbosity_distribution"].get("high", 0)
    
    if exploratory_high_verbosity > 0.5 and casual_high_verbosity < 0.1:
        biases.append({
            "type": "verbosity_bias",
            "archetype": "exploratory vs casual",
            "description": f"Exploratory users get {exploratory_high_verbosity:.1%} high verbosity, casual users get {casual_high_verbosity:.1%}",
            "risk": "moderate",
            "recommendation": "Verbosity may be biased toward reflective users"
        })
    
    return biases


def classify_signal_universality(archetype_stats):
    """
    Classify signals as universal, contextual, or personal.
    """
    signal_names = ["depth_requested", "alignment_signal", "tools_requested"]
    classifications = {}
    
    for signal_name in signal_names:
        frequencies = [stats["signal_frequency"][signal_name] for stats in archetype_stats]
        
        # Calculate variance
        mean_freq = sum(frequencies) / len(frequencies)
        variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
        std_dev = variance ** 0.5
        
        # Classify based on variance
        if std_dev < 0.15:
            # Low variance = universal
            classifications[signal_name] = {
                "category": "universal",
                "safety": "safe",
                "mean_frequency": mean_freq,
                "std_dev": std_dev,
                "recommendation": "Safe for all users"
            }
        elif std_dev < 0.30:
            # Medium variance = contextual
            classifications[signal_name] = {
                "category": "contextual",
                "safety": "needs_gating",
                "mean_frequency": mean_freq,
                "std_dev": std_dev,
                "recommendation": "Safe when confidence ≥ 0.7"
            }
        else:
            # High variance = personal
            classifications[signal_name] = {
                "category": "personal",
                "safety": "do_not_activate_globally",
                "mean_frequency": mean_freq,
                "std_dev": std_dev,
                "recommendation": "Do not activate without explicit user request"
            }
    
    return classifications


def generate_activation_safety_map(archetype_stats, signal_classifications):
    """
    Generate safety map for activation decisions.
    """
    safety_map = {
        "all_users": [],
        "confidence_gated": [],
        "never_without_request": [],
    }
    
    # Classify signals
    for signal_name, classification in signal_classifications.items():
        if classification["category"] == "universal":
            safety_map["all_users"].append(signal_name)
        elif classification["category"] == "contextual":
            safety_map["confidence_gated"].append(signal_name)
        else:
            safety_map["never_without_request"].append(signal_name)
    
    # Classify mediator decisions
    mediator_decisions = ["show_reasoning", "ask_clarifying_question"]
    
    for decision_name in mediator_decisions:
        frequencies = [stats["mediator_frequency"][decision_name] for stats in archetype_stats]
        mean_freq = sum(frequencies) / len(frequencies)
        variance = sum((f - mean_freq) ** 2 for f in frequencies) / len(frequencies)
        std_dev = variance ** 0.5
        
        if std_dev < 0.15:
            safety_map["all_users"].append(decision_name)
        elif std_dev < 0.30:
            safety_map["confidence_gated"].append(decision_name)
        else:
            safety_map["never_without_request"].append(decision_name)
    
    # Verbosity and structure need special handling
    verbosity_variance = []
    structure_variance = []
    
    for stats in archetype_stats:
        verbosity_dist = stats["verbosity_distribution"]
        structure_dist = stats["structure_distribution"]
        
        # Check if distributions are stable
        verbosity_variance.append(max(verbosity_dist.values()) - min(verbosity_dist.values()))
        structure_variance.append(max(structure_dist.values()) - min(structure_dist.values()))
    
    avg_verbosity_variance = sum(verbosity_variance) / len(verbosity_variance)
    avg_structure_variance = sum(structure_variance) / len(structure_variance)
    
    if avg_structure_variance < 0.3:
        safety_map["all_users"].append("structure")
    else:
        safety_map["confidence_gated"].append("structure")
    
    if avg_verbosity_variance < 0.3:
        safety_map["confidence_gated"].append("verbosity")
    else:
        safety_map["never_without_request"].append("verbosity")
    
    return safety_map


def generate_report():
    """
    Generate complete overfitting & generalization report.
    """
    print("="*80)
    print("PROMPT 8: OVERFITTING & GENERALIZATION AUDIT")
    print("="*80)
    print()
    
    # Analyze each archetype
    casual_stats = analyze_archetype("casual", CASUAL_USER_TURNS)
    task_stats = analyze_archetype("task_oriented", TASK_ORIENTED_USER_TURNS)
    exploratory_stats = analyze_archetype("exploratory", EXPLORATORY_USER_TURNS)
    
    all_stats = [casual_stats, task_stats, exploratory_stats]
    
    # Print archetype summaries
    print("ARCHETYPE SUMMARIES")
    print("="*80)
    for stats in all_stats:
        print(f"\n{stats['archetype'].upper()}")
        print(f"  Sample Size: {stats['sample_size']}")
        print(f"  Avg Message Length: {stats['avg_message_length']:.0f} chars")
        print(f"  Avg Confidence: {stats['avg_confidence']:.2f}")
        print(f"\n  Signal Frequency:")
        for signal, freq in stats['signal_frequency'].items():
            print(f"    {signal:20s}: {freq:5.1%}")
        print(f"\n  Query Type Distribution:")
        for qtype, freq in stats['query_type_distribution'].items():
            print(f"    {qtype:20s}: {freq:5.1%}")
        print(f"\n  Mediator Decisions:")
        for decision, freq in stats['mediator_frequency'].items():
            print(f"    {decision:25s}: {freq:5.1%}")
        print(f"\n  Verbosity Distribution:")
        for verb, freq in stats['verbosity_distribution'].items():
            print(f"    {verb:20s}: {freq:5.1%}")
    
    print()
    print("="*80)
    print("SIGNAL UNIVERSALITY ANALYSIS")
    print("="*80)
    
    signal_classifications = classify_signal_universality(all_stats)
    
    for signal_name, classification in signal_classifications.items():
        print(f"\n{signal_name}:")
        print(f"  Category: {classification['category']}")
        print(f"  Safety: {classification['safety']}")
        print(f"  Mean Frequency: {classification['mean_frequency']:.1%}")
        print(f"  Std Dev: {classification['std_dev']:.2f}")
        print(f"  Recommendation: {classification['recommendation']}")
    
    print()
    print("="*80)
    print("BIAS DETECTION")
    print("="*80)
    
    biases = detect_bias(all_stats)
    
    if biases:
        for bias in biases:
            print(f"\n{bias['type'].upper()} - {bias['archetype']}")
            print(f"  Description: {bias['description']}")
            print(f"  Risk: {bias['risk']}")
            print(f"  Recommendation: {bias['recommendation']}")
    else:
        print("\nNo significant biases detected.")
    
    print()
    print("="*80)
    print("ACTIVATION SAFETY MAP")
    print("="*80)
    
    safety_map = generate_activation_safety_map(all_stats, signal_classifications)
    
    print("\nSafe for ALL USERS:")
    for item in safety_map["all_users"]:
        print(f"  ✅ {item}")
    
    print("\nSafe when CONFIDENCE ≥ 0.7:")
    for item in safety_map["confidence_gated"]:
        print(f"  ⚠️  {item}")
    
    print("\nNEVER without explicit user request:")
    for item in safety_map["never_without_request"]:
        print(f"  ❌ {item}")
    
    print()
    print("="*80)
    print("STABILITY CHECK")
    print("="*80)
    
    # Check confidence stability
    confidences = [stats["avg_confidence"] for stats in all_stats]
    confidence_variance = sum((c - sum(confidences)/len(confidences)) ** 2 for c in confidences) / len(confidences)
    confidence_std_dev = confidence_variance ** 0.5
    
    print(f"\nConfidence Scores Across Archetypes:")
    for stats in all_stats:
        print(f"  {stats['archetype']:20s}: {stats['avg_confidence']:.2f}")
    print(f"\nStd Dev: {confidence_std_dev:.3f}")
    
    if confidence_std_dev < 0.1:
        print("✅ Confidence scores are STABLE across archetypes")
    else:
        print("⚠️  Confidence scores vary across archetypes")
    
    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    return {
        "archetype_stats": all_stats,
        "signal_classifications": signal_classifications,
        "biases": biases,
        "safety_map": safety_map,
        "confidence_stability": {
            "std_dev": confidence_std_dev,
            "stable": confidence_std_dev < 0.1
        }
    }


if __name__ == "__main__":
    analysis = generate_report()
