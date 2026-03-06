from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError


def _valid_request_kwargs():
    return {
        "userId": "user_1",
        "monthlyBudget": 300.0,
        "weight": 170.0,
        "goalType": "maintain",
        "dietaryTags": [],
        "allergies": [],
    }


def test_budget_validation_bounds_and_precision():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest

        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "monthlyBudget": 49.99})
        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "monthlyBudget": 1000.01})
        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "monthlyBudget": 250.123})


def test_weight_validation_bounds_and_precision():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest

        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "weight": 99.9})
        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "weight": 380.1})
        with pytest.raises(ValidationError):
            PlanGenerationRequest(**{**_valid_request_kwargs(), "weight": 170.12})


def test_acquire_generation_lock_conflict_when_active_and_not_expired():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import GenerationConflictError, _acquire_generation_lock_txn

        now = datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc)
        user_ref = MagicMock()
        user_ref.get.return_value.to_dict.return_value = {
            "activeGeneration": {
                "status": "running",
                "expiresAt": now + timedelta(minutes=5),
            }
        }
        transaction = MagicMock()

        with pytest.raises(GenerationConflictError):
            _acquire_generation_lock_txn.to_wrap(
                transaction,
                user_ref,
                "user_1",
                "request_1",
                "2026-03",
                now,
                now + timedelta(minutes=10),
            )


def test_acquire_generation_lock_replaces_stale_lock():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import _acquire_generation_lock_txn

        now = datetime(2026, 3, 5, 10, 0, tzinfo=timezone.utc)
        user_ref = MagicMock()
        user_ref.get.return_value.to_dict.return_value = {
            "activeGeneration": {
                "status": "running",
                "expiresAt": now - timedelta(minutes=1),
                "requestId": "old_req",
            }
        }
        transaction = MagicMock()

        _acquire_generation_lock_txn.to_wrap(
            transaction,
            user_ref,
            "user_1",
            "new_req",
            "2026-03",
            now,
            now + timedelta(minutes=10),
        )

        assert transaction.set.call_count == 1
        payload = transaction.set.call_args.args[1]
        assert payload["activeGeneration"]["status"] == "running"
        assert payload["activeGeneration"]["requestId"] == "new_req"


def test_resolve_target_month_uses_next_month_when_ready_plan_exists():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import resolve_target_month

        ready_doc = MagicMock()
        ready_doc.to_dict.return_value = {"status": "ready", "planMonth": "2026-03"}
        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.where.return_value.stream.return_value = [
            ready_doc
        ]

        with patch("db.plan_service.db", mock_db):
            with patch("db.plan_service._utcnow", return_value=datetime(2026, 3, 5, tzinfo=timezone.utc)):
                assert resolve_target_month("user_1") == "2026-04"


def test_get_next_plan_version_increments_for_same_month():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import get_next_plan_version

        doc_v1 = MagicMock()
        doc_v1.to_dict.return_value = {"version": 1}
        doc_v3 = MagicMock()
        doc_v3.to_dict.return_value = {"version": 3}

        mock_db = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.where.return_value.stream.return_value = [
            doc_v1,
            doc_v3,
        ]

        with patch("db.plan_service.db", mock_db):
            assert get_next_plan_version("user_1", "2026-03") == 4


def test_generate_and_store_plan_releases_lock_after_success():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(**_valid_request_kwargs())
        fake_gemini = MagicMock(mealPlan=[], ingredientPrices={})

        with patch("db.plan_service.db", MagicMock()):
            with patch("db.plan_service.resolve_target_month", return_value="2026-03"):
                with patch("db.plan_service.get_next_plan_version", return_value=1):
                    with patch("db.plan_service.acquire_generation_lock", return_value=("req_1", datetime.now(timezone.utc))):
                        with patch("db.plan_service.persist_user_plan"):
                            with patch("db.plan_service.generate_meal_plan", return_value=fake_gemini):
                                with patch("db.plan_service.upsert_ingredient_prices", return_value={}):
                                    with patch("db.plan_service.build_normalized_name_map", return_value={}):
                                        with patch("db.plan_service.build_price_hint_map", return_value={}):
                                            with patch("db.plan_service.recalculate_meal_costs", return_value=([], 0.0)):
                                                with patch("db.plan_service.dedupe_or_create_recipes", return_value=([], {"recipesCreated": 0, "recipesReused": 0})):
                                                    with patch("db.plan_service.apply_diversity_selection", return_value=([], {"scoredCount": 0, "selectedCount": 0})):
                                                        with patch("db.plan_service.enforce_budget_with_swaps", return_value=([], {"budgetExceededInitially": False, "swapsApplied": 0, "mealsDropped": 0, "finalTotalCost": 0.0, "budgetMet": True})):
                                                            with patch("db.plan_service.aggregate_grocery_list", return_value=[]):
                                                                with patch("db.plan_service.chunk_meals_into_weeks", return_value=[]):
                                                                    with patch("db.plan_service.supersede_ready_plans_for_month", return_value=0):
                                                                        with patch("db.plan_service.append_meal_history", return_value=0):
                                                                            with patch("db.plan_service.release_generation_lock") as mock_release:
                                                                                generate_and_store_plan(request)

        mock_release.assert_called_once_with("user_1", "req_1", "ready")


def test_generate_and_store_plan_releases_lock_after_exception():
    with patch("db.firestore_client.db", MagicMock()):
        from db.plan_service import PlanGenerationRequest, generate_and_store_plan

        request = PlanGenerationRequest(**_valid_request_kwargs())
        with patch("db.plan_service.db", MagicMock()):
            with patch("db.plan_service.resolve_target_month", return_value="2026-03"):
                with patch("db.plan_service.get_next_plan_version", return_value=1):
                    with patch("db.plan_service.acquire_generation_lock", return_value=("req_1", datetime.now(timezone.utc))):
                        with patch("db.plan_service.persist_user_plan"):
                            with patch("db.plan_service.generate_meal_plan", side_effect=RuntimeError("boom")):
                                with patch("db.plan_service.update_plan_status"):
                                    with patch("db.plan_service.release_generation_lock") as mock_release:
                                        with pytest.raises(ValueError, match="Failed to generate/store plan"):
                                            generate_and_store_plan(request)

        mock_release.assert_called_once_with("user_1", "req_1", "failed")
