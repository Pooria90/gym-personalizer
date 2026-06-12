from gym_pt.retrieval import (
    DEFAULT_CATALOG_PATH,
    ExerciseCatalogLoader,
    exercise_embedding_text,
    load_catalog,
)

import pytest


class TestExerciseEmbeddingText:
    def test_contains_search_relevant_fields(self, exercise_factory):
        ex = exercise_factory(
            "Cable_Curl",
            name="Cable Curl",
            equipment="cable",
            primaryMuscles=["biceps"],
            secondaryMuscles=["forearms"],
            mechanic="isolation",
            force="pull",
        )
        text = exercise_embedding_text(ex)
        for needle in (
            "Cable Curl",
            "strength exercise",
            "beginner level",
            "isolation",
            "pull movement",
            "equipment: cable",
            "biceps",
            "forearms",
            ex.instructions[0],
        ):
            assert needle in text

    def test_handles_missing_optional_fields(self, exercise_factory):
        ex = exercise_factory(
            "Push_Up", equipment=None, mechanic=None, force=None, secondaryMuscles=[]
        )
        text = exercise_embedding_text(ex)
        assert "equipment: none" in text
        assert "None" not in text
        assert "Secondary muscles" not in text

    def test_deterministic(self, exercise_factory):
        ex = exercise_factory("Barbell_Squat")
        assert exercise_embedding_text(ex) == exercise_embedding_text(ex)


class TestExerciseCatalogLoader:
    async def test_one_document_per_exercise_with_unique_sources(self, tiny_dataset):
        path, catalog = tiny_dataset
        docs = [doc async for doc in ExerciseCatalogLoader(path).astream()]
        assert len(docs) == len(catalog)
        # Unique per-exercise sources (and therefore document ids) are what
        # make the runtime's upsert/skip-unchanged semantics work per
        # exercise rather than per file.
        assert len({doc.source for doc in docs}) == len(docs)
        assert len({doc.id for doc in docs}) == len(docs)

    async def test_document_ids_stable_across_runs(self, tiny_dataset):
        path, _ = tiny_dataset
        first = {
            doc.source: doc.id async for doc in ExerciseCatalogLoader(path).astream()
        }
        second = {
            doc.source: doc.id async for doc in ExerciseCatalogLoader(path).astream()
        }
        assert first == second

    async def test_metadata_carries_filter_fields(self, tiny_dataset):
        path, catalog = tiny_dataset
        docs = {
            doc.metadata["exercise_id"]: doc
            async for doc in ExerciseCatalogLoader(path).astream()
        }
        assert set(docs) == set(catalog)
        squat = docs["Barbell_Squat"]
        assert squat.metadata["level"] == "beginner"
        assert squat.metadata["category"] == "strength"
        assert squat.metadata["equipment"] == "barbell"
        # None equipment is omitted, not stored as null
        assert "equipment" not in docs["Push_Up"].metadata

    async def test_limit(self, tiny_dataset):
        path, _ = tiny_dataset
        docs = [doc async for doc in ExerciseCatalogLoader(path, limit=2).astream()]
        assert len(docs) == 2


class TestLoadCatalog:
    def test_maps_ids_to_exercises(self, tiny_dataset):
        path, expected = tiny_dataset
        catalog = load_catalog(path)
        assert set(catalog) == set(expected)
        assert catalog["Barbell_Squat"].name == "Barbell Squat"

    @pytest.mark.skipif(
        not DEFAULT_CATALOG_PATH.exists(),
        reason="free-exercise-db dataset not present",
    )
    def test_real_dataset_loads_fully(self):
        catalog = load_catalog()
        assert len(catalog) == 873
        assert all(eid == ex.id for eid, ex in catalog.items())
