"""
PROMPT 7: Shadow Mediator Accuracy Analysis

Runs synthetic test data through actual instrumentation logic
and validates shadow mediator accuracy.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from turn_instrumentation import instrument_user_turn, classify_query_type, detect_depth_requested, detect_alignment_signal, detect_tools_requested
from conversation_mediator import ShadowConversationMediator
from PROMPT7_SYNTHETIC_TEST_DATA import SYNTHETIC_TEST_TURNS


def analyze_turn(turn_data):
    """
    Analyze a single turn through the instrumentation pipeline.
    
    Returns:
        dict with actual vs expected signals and mediator decisions
    """
    user_message = turn_data["user_message"]
    
    # Run actual instrumentation
    actual_metadata = instrument_user_turn(
        query=user_message,
        epistemic_query_type=turn_data["expected_signals"].get("epistemic_query_type")
    )
    
    # Run shadow mediator
    mediator = ShadowConversationMediator()
    mediator_decision = mediator.compute_decision(
        query=user_message,
        recent_turns=[],
        query_metadata=actual_metadata
    )
    
    # Compare actual vs expected
    expected_signals = turn_data["expected_signals"]
    expected_mediator = turn_data["expected_mediator"]
    
    signal_matches = {
        "query_type": actual_metadata["query_type"] == expected_signals["query_type"],
        "depth_requested": actual_metadata["depth_requested"] == expected_signals["depth_requested"],
        "alignment_signal": actual_metadata["alignment_signal"] == expected_signals["alignment_signal"],
        "tools_requested": actual_metadata["tools_requested"] == expected_signals["tools_requested"],
    }
    
    mediator_matches = {
        "verbosity": mediator_decision.verbosity == expected_mediator["verbosity"],
        "structure": mediator_decision.structure == expected_mediator["structure"],
        "show_reasoning": mediator_decision.show_reasoning == expected_mediator["show_reasoning"],
        "ask_clarifying_question": mediator_decision.ask_clarifying_question == expected_mediator.get("ask_clarifying_question", False),
    }
    
    return {
        "turn_index": turn_data["turn_index"],
        "user_message": user_message,
        "context": turn_data["context"],
        "actual_signals": {
            "query_type": actual_metadata["query_type"],
            "depth_requested": actual_metadata["depth_requested"],
            "alignment_signal": actual_metadata["alignment_signal"],
            "tools_requested": actual_metadata["tools_requested"],
        },
        "expected_signals": expected_signals,
        "signal_matches": signal_matches,
        "signal_accuracy": sum(signal_matches.values()) / len(signal_matches),
        "actual_mediator": {
            "verbosity": mediator_decision.verbosity,
            "structure": mediator_decision.structure,
            "show_reasoning": mediator_decision.show_reasoning,
            "ask_clarifying_question": mediator_decision.ask_clarifying_question,
            "confidence": mediator_decision.confidence,
            "signals_used": mediator_decision.signals_used,
            "reasoning": mediator_decision.reasoning,
        },
        "expected_mediator": expected_mediator,
        "mediator_matches": mediator_matches,
        "mediator_accuracy": sum(mediator_matches.values()) / len(mediator_matches),
    }


def categorize_results(results):
    """
    Categorize results into wins, misses, and ambiguous cases.
    """
    wins = []
    misses = []
    ambiguous = []
    
    for result in results:
        signal_acc = result["signal_accuracy"]
        mediator_acc = result["mediator_accuracy"]
        
        # Win: Both signal and mediator accuracy >= 0.75
        if signal_acc >= 0.75 and mediator_acc >= 0.75:
            wins.append(result)
        # Miss: Either signal or mediator accuracy < 0.5
        elif signal_acc < 0.5 or mediator_acc < 0.5:
            misses.append(result)
        # Ambiguous: Everything else
        else:
            ambiguous.append(result)
    
    return wins, misses, ambiguous


def analyze_signal_quality(results):
    """
    Analyze which signals are high-trust vs noisy.
    """
    signal_names = ["query_type", "depth_requested", "alignment_signal", "tools_requested"]
    signal_accuracy = {name: [] for name in signal_names}
    
    for result in results:
        for signal_name in signal_names:
            match = result["signal_matches"][signal_name]
            signal_accuracy[signal_name].append(1.0 if match else 0.0)
    
    signal_quality = {}
    for signal_name, accuracies in signal_accuracy.items():
        avg_accuracy = sum(accuracies) / len(accuracies)
        if avg_accuracy >= 0.85:
            quality = "HIGH-TRUST"
        elif avg_accuracy >= 0.65:
            quality = "MODERATE"
        else:
            quality = "NOISY"
        
        signal_quality[signal_name] = {
            "accuracy": avg_accuracy,
            "quality": quality
        }
    
    return signal_quality


def analyze_mediator_quality(results):
    """
    Analyze mediator decision quality.
    """
    decision_names = ["verbosity", "structure", "show_reasoning", "ask_clarifying_question"]
    decision_accuracy = {name: [] for name in decision_names}
    
    for result in results:
        for decision_name in decision_names:
            match = result["mediator_matches"][decision_name]
            decision_accuracy[decision_name].append(1.0 if match else 0.0)
    
    decision_quality = {}
    for decision_name, accuracies in decision_accuracy.items():
        avg_accuracy = sum(accuracies) / len(accuracies)
        if avg_accuracy >= 0.85:
            quality = "HIGH-TRUST"
        elif avg_accuracy >= 0.65:
            quality = "MODERATE"
        else:
            quality = "NOISY"
        
        decision_quality[decision_name] = {
            "accuracy": avg_accuracy,
            "quality": quality
        }
    
    return decision_quality


def generate_report():
    """
    Generate complete accuracy analysis report.
    """
    print("="*80)
    print("PROMPT 7: SHADOW MEDIATOR ACCURACY REVIEW")
    print("="*80)
    print()
    
    # Run analysis on all test turns
    results = [analyze_turn(turn) for turn in SYNTHETIC_TEST_TURNS]
    
    # Categorize results
    wins, misses, ambiguous = categorize_results(results)
    
    print(f"Total Test Turns: {len(results)}")
    print(f"Clear Wins: {len(wins)} ({len(wins)/len(results)*100:.1f}%)")
    print(f"Clear Misses: {len(misses)} ({len(misses)/len(results)*100:.1f}%)")
    print(f"Ambiguous: {len(ambiguous)} ({len(ambiguous)/len(results)*100:.1f}%)")
    print()
    
    # Signal quality analysis
    print("="*80)
    print("SIGNAL QUALITY ASSESSMENT")
    print("="*80)
    signal_quality = analyze_signal_quality(results)
    for signal_name, quality_data in signal_quality.items():
        print(f"{signal_name:20s}: {quality_data['accuracy']:5.1%} - {quality_data['quality']}")
    print()
    
    # Mediator decision quality
    print("="*80)
    print("MEDIATOR DECISION QUALITY")
    print("="*80)
    decision_quality = analyze_mediator_quality(results)
    for decision_name, quality_data in decision_quality.items():
        print(f"{decision_name:25s}: {quality_data['accuracy']:5.1%} - {quality_data['quality']}")
    print()
    
    # Show example wins
    print("="*80)
    print("CLEAR WINS (First 3)")
    print("="*80)
    for i, result in enumerate(wins[:3], 1):
        print(f"\n--- WIN {i} ---")
        print(f"Turn {result['turn_index']}: {result['context']}")
        print(f"User: \"{result['user_message']}\"")
        print(f"Signal Accuracy: {result['signal_accuracy']:.1%}")
        print(f"Mediator Accuracy: {result['mediator_accuracy']:.1%}")
        print(f"Mediator Decision: verbosity={result['actual_mediator']['verbosity']}, "
              f"show_reasoning={result['actual_mediator']['show_reasoning']}, "
              f"confidence={result['actual_mediator']['confidence']:.2f}")
        print(f"Reasoning: {result['actual_mediator']['reasoning']}")
    
    # Show example misses
    print()
    print("="*80)
    print("CLEAR MISSES (First 3)")
    print("="*80)
    for i, result in enumerate(misses[:3], 1):
        print(f"\n--- MISS {i} ---")
        print(f"Turn {result['turn_index']}: {result['context']}")
        print(f"User: \"{result['user_message']}\"")
        print(f"Signal Accuracy: {result['signal_accuracy']:.1%}")
        print(f"Mediator Accuracy: {result['mediator_accuracy']:.1%}")
        print("\nSignal Mismatches:")
        for signal_name, match in result['signal_matches'].items():
            if not match:
                print(f"  {signal_name}: expected={result['expected_signals'][signal_name]}, "
                      f"actual={result['actual_signals'][signal_name]}")
        print("\nMediator Mismatches:")
        for decision_name, match in result['mediator_matches'].items():
            if not match:
                print(f"  {decision_name}: expected={result['expected_mediator'][decision_name]}, "
                      f"actual={result['actual_mediator'][decision_name]}")
    
    # Show ambiguous cases
    print()
    print("="*80)
    print("AMBIGUOUS CASES (First 3)")
    print("="*80)
    for i, result in enumerate(ambiguous[:3], 1):
        print(f"\n--- AMBIGUOUS {i} ---")
        print(f"Turn {result['turn_index']}: {result['context']}")
        print(f"User: \"{result['user_message']}\"")
        print(f"Signal Accuracy: {result['signal_accuracy']:.1%}")
        print(f"Mediator Accuracy: {result['mediator_accuracy']:.1%}")
        print(f"Mediator Confidence: {result['actual_mediator']['confidence']:.2f}")
    
    print()
    print("="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    
    return {
        "results": results,
        "wins": wins,
        "misses": misses,
        "ambiguous": ambiguous,
        "signal_quality": signal_quality,
        "decision_quality": decision_quality
    }


if __name__ == "__main__":
    analysis = generate_report()
