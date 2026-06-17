import json

from core.knowledge.ike2.etl.bulk_inject import inject, load_dump


class FakeWriter:
    """In-memory stand-in for the DB so orchestration is testable without Supabase."""

    def __init__(self):
        self.groups = {}      # canonical_name -> row (with "id")
        self.ingredients = {}  # (gid, name) -> iid
        self.aliases = set()   # (norm, iid, region)
        self.rejects = []
        self._seq = 0

    def _next(self, prefix):
        self._seq += 1
        return f"{prefix}{self._seq}"

    def seed_group(self, row):
        gid = self._next("g")
        self.groups[row["canonical_name"]] = {**row, "id": gid}
        return gid

    def get_group(self, canonical_name):
        return self.groups.get(canonical_name)

    def insert_group(self, row):
        gid = self._next("g")
        self.groups[row["canonical_name"]] = {**row, "id": gid}
        return gid

    def update_group(self, gid, result):
        for name, g in self.groups.items():
            if g["id"] == gid:
                g.update(result.merged_flags)
                g["knowledge_state"] = result.knowledge_state
                return

    def upsert_ingredient(self, gid, normalized_name, source):
        key = (gid, normalized_name)
        if key not in self.ingredients:
            self.ingredients[key] = self._next("i")
        return self.ingredients[key]

    def upsert_alias(self, normalized_alias, ingredient_id, region, source):
        key = (normalized_alias, ingredient_id, region)
        if key in self.aliases:
            return False
        self.aliases.add(key)
        return True

    def quarantine(self, reject, source):
        self.rejects.append(reject)


def _rec(**over):
    base = {"canonical_name": "carrot", "plant_origin": True,
            "aliases": ["carrot"], "regions": ["Global"]}
    base.update(over)
    return base


def test_new_record_is_inserted_with_ingredient_and_alias():
    w = FakeWriter()
    stats = inject([_rec()], "usda", w)
    assert stats.inserted == 1
    assert stats.ingredients == 1
    assert stats.aliases == 1
    assert w.get_group("carrot")["plant_origin"] is True


def test_existing_group_reconciles_most_restrictive_and_flags_review():
    w = FakeWriter()
    w.seed_group({"canonical_name": "whey", "animal_origin": True,
                  "dairy_source": False, "knowledge_state": "AUTO_CLASSIFIED"})
    stats = inject([_rec(canonical_name="whey", animal_origin=True,
                         dairy_source=True, plant_origin=False, aliases=["whey"])],
                   "openfoodfacts", w)
    assert stats.inserted == 0
    assert stats.updated == 1
    assert stats.needs_review == 1
    assert w.get_group("whey")["dairy_source"] is True  # most restrictive wins


def test_invalid_row_is_quarantined_and_batch_continues():
    w = FakeWriter()
    # insect_derived without animal_origin violates insect_implies_animal
    bad = _rec(canonical_name="mystery_dye", insect_derived=True,
               animal_origin=False, plant_origin=False, aliases=["mystery_dye"])
    good = _rec(canonical_name="spinach", aliases=["spinach"])
    stats = inject([bad, good], "wikidata", w)
    assert stats.rejected == 1
    assert stats.inserted == 1
    assert len(w.rejects) == 1
    assert w.rejects[0]["violated_constraint"] == "insect_implies_animal"
    assert w.get_group("spinach") is not None
    assert w.get_group("mystery_dye") is None


def test_rerun_is_idempotent():
    w = FakeWriter()
    recs = [_rec()]
    inject(recs, "usda", w)
    stats2 = inject(recs, "usda", w)
    # second run finds the group, so it updates rather than inserts, and adds no
    # duplicate ingredient/alias rows
    assert stats2.inserted == 0
    assert stats2.updated == 1
    assert stats2.aliases == 0
    assert len(w.groups) == 1
    assert len(w.ingredients) == 1
    assert len(w.aliases) == 1


def test_load_dump_handles_wrapped_and_bare_shapes(tmp_path):
    wrapped = tmp_path / "wrapped.json"
    wrapped.write_text(json.dumps({"source": "wikidata", "ingredients": [_rec()]}))
    src, records = load_dump(str(wrapped))
    assert src == "wikidata"
    assert len(records) == 1

    bare = tmp_path / "bare.json"
    bare.write_text(json.dumps([_rec(), _rec(canonical_name="beet")]))
    src2, records2 = load_dump(str(bare))
    assert src2 is None
    assert len(records2) == 2
