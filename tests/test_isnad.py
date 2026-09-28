"""Unit tests for the isnad parser, on real chains from the six books.

Every isnad is read verbatim from data/hadiths.json.gz by its id (LK Hadith
Corpus); nothing here is written by hand except the expected reading of the
chain, which uses only words that appear in that isnad. Run:

    python -m unittest discover -s tests -v
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from sanad_core import engine  # noqa: E402
from sanad_core.isnad import parse_isnad, quote, canonical  # noqa: E402


def parsed(hid):
    h = engine.data()["hadiths"][engine.data()["by_id"][hid]]
    return h, parse_isnad(h["isnad"], h["matn"])


def names(route):
    return [n["name"] for n in route["names"]]


class PlainChains(unittest.TestCase):
    def test_bukhari_1_single_route(self):
        _, p = parsed("bukhari-1")
        self.assertEqual(len(p["routes"]), 1)
        self.assertEqual(names(p["routes"][0]), [
            "الحميدي عبدالله بن الزبير", "سفيان", "يحيي بن سعيد الانصاري",
            "محمد بن ابراهيم التيمي", "علقمه بن وقاص الليثي", "عمر بن الخطاب"])
        self.assertTrue(p["to_prophet"])
        self.assertFalse(p["tahwil"])

    def test_every_name_quotes_its_original_words(self):
        h, p = parsed("bukhari-1")
        first = p["routes"][0]["names"][0]
        q = quote(h["isnad"], h["matn"], first["span"])
        self.assertIn("الْحُمَيْدِيُّ", q)          # verbatim, with diacritics
        self.assertTrue(h["isnad"].find(q.split()[0]) >= 0)

    def test_segmentation_repair_moves_companion_back(self):
        # isnad ends "أن أبا", matn starts "هريرة كان يصلي ..."
        _, p = parsed("muslim-864")
        self.assertEqual(names(p["routes"][0])[-1], "ابو هريره")


class NoiseIsNotAName(unittest.TestCase):
    def test_narration_after_companion_dropped(self):
        # "... عن أنس قال كان ..."
        _, p = parsed("bukhari-2817")
        self.assertEqual(names(p["routes"][0]), ["احمد بن عبد الملك بن واقد", "حماد بن زيد", "ثابت", "انس"])

    def test_lamma_dropped(self):
        # "... عن أنس قال لما كان يوم أحد"
        _, p = parsed("bukhari-2876")
        self.assertNotIn("لما", [n for r in p["routes"] for n in names(r)])

    def test_wording_note_is_not_a_narrator(self):
        # "قال أحمد حدثنا وقال الآخران أخبرنا ابن وهب"
        _, p = parsed("muslim-125")
        all_names = {n for r in p["routes"] for n in names(r)}
        self.assertNotIn("الاخران", all_names)
        self.assertNotIn("احمد", all_names)
        self.assertEqual(len(p["routes"]), 3)

    def test_listener_after_yuhaddith_is_not_a_narrator(self):
        # "سمع عباد بن تميم يحدث أباه عن عمه عبد الله بن زيد"
        _, p = parsed("bukhari-1012")
        self.assertEqual(names(p["routes"][0])[-2:], ["عباد بن تميم", "عبد الله بن زيد"])

    def test_verb_inside_piece_ends_name(self):
        # "قال محمد بن بشار سألت يحيى بن سعيد عن هذا الحديث فحدثني عن شعبة"
        _, p = parsed("tirmidhi-565")
        self.assertEqual(names(p["routes"][0])[:3], ["محمد بن بشار", "يحيي بن سعيد", "شعبه"])


class CoNarrators(unittest.TestCase):
    def test_two_narrators_joined_by_waw(self):
        # "حدثنا أبو بكر بن أبي شيبة وهشام بن عمار قالا حدثنا سفيان بن عيينة"
        _, p = parsed("ibnmajah-831")
        heads = [names(r)[0] for r in p["routes"]]
        self.assertEqual(heads, ["ابو بكر بن ابي شيبه", "هشام بن عمار"])
        self.assertTrue(all(names(r)[1] == "سفيان بن عيينه" for r in p["routes"]))

    def test_trailing_restatement_is_not_a_narrator(self):
        # the isnad ends "... عن أمه قال أبو بكر بن أبي شيبة"
        _, p = parsed("ibnmajah-831")
        for r in p["routes"]:
            self.assertNotEqual(names(r)[-1], "ابو بكر بن ابي شيبه")

    def test_explanation_then_co_narrator(self):
        # "حدثنا أبو عبيدة بن أبي السفر وهو أحمد بن عبد الله ... وإسحاق بن منصور"
        _, p = parsed("tirmidhi-87")
        self.assertEqual([names(r)[0] for r in p["routes"]], ["ابو عبيده بن ابي السفر", "اسحاق بن منصور"])
        self.assertEqual(names(p["routes"][0])[1], "عبد الصمد بن عبد الوارث")

    def test_bare_abi_then_co_narrator(self):
        # "حدثنا ابن نمير حدثنا أبي ومحمد بن بشر"
        _, p = parsed("muslim-7035")
        second = {names(r)[1] for r in p["routes"] if names(r)[0] == "ابن نمير"}
        self.assertIn("محمد بن بشر", second)
        self.assertNotIn("ابو ومحمد بن بشر", second)

    def test_doubt_between_two_keeps_both_uncertain(self):
        # "عن أبي هريرة أو عن أبي سعيد شك الأعمش"
        _, p = parsed("muslim-138")
        tops = {r["names"][-1]["name"]: r["names"][-1] for r in p["routes"]}
        self.assertEqual(set(tops), {"ابو هريره", "ابو سعيد"})
        self.assertTrue(all(n["uncertain"] and n.get("doubt") for n in tops.values()))


class Tahwil(unittest.TestCase):
    def test_kilahuma_joins_previous_segment(self):
        # "... حدثنا أبو الأحوص ح وحدثنا قتيبة وإسحاق عن جرير كلاهما عن عبد العزيز بن رفيع"
        _, p = parsed("muslim-2800")
        self.assertEqual(len(p["routes"]), 3)
        first = next(r for r in p["routes"] if names(r)[0] == "ابو بكر بن ابي شيبه")
        self.assertEqual(names(first), ["ابو بكر بن ابي شيبه", "ابو الاحوص", "عبد العزيز بن رفيع",
                                        "عبد الله بن ابي قتاده"])
        self.assertEqual(first["join"], "convergence")

    def test_kulluhum_joins_all_open_segments(self):
        # four segments, "... عن الأوزاعي كلهم عن الزهري"
        _, p = parsed("abudawud-235")
        self.assertEqual(len(p["routes"]), 4)
        self.assertTrue(all(names(r)[-3:] == ["الزهري", "ابو سلمه", "ابو هريره"] for r in p["routes"]))
        self.assertEqual(p["fragments"], [])

    def test_nested_convergence(self):
        # "كلاهما عن شعبة" then "كل هؤلاء عن عبد الملك بن عمير": six routes
        _, p = parsed("muslim-4414")
        self.assertEqual(len(p["routes"]), 6)
        self.assertTrue(all(names(r)[-3] == "عبد الملك بن عمير" for r in p["routes"]))
        ubaid = next(r for r in p["routes"] if names(r)[0] == "عبيد الله بن معاذ")
        self.assertEqual(names(ubaid)[1:3], ["معاذ", "شعبه"])     # "حدثنا أبي" -> father from the name
        self.assertTrue(ubaid["names"][1]["relative"])

    def test_shared_name_join(self):
        # "... عن ابن عجلان ح ... حدثنا أبو خالد الأحمر عن ابن عجلان عن عامر"
        _, p = parsed("muslim-1290")
        q = next(r for r in p["routes"] if names(r)[0] == "قتيبه")
        self.assertEqual(q["join"], "shared_name")
        self.assertEqual(names(q)[2:4], ["ابن عجلان", "عامر بن عبد الله بن الزبير"])

    def test_within_segment_jamian_does_not_join_other_segments(self):
        # "زهير ومحمد بن المثنى وابن بشار جميعا عن يحيى القطان"
        _, p = parsed("muslim-7053")
        wakee = next(r for r in p["routes"] if names(r)[0] == "ابو بكر بن ابي شيبه")
        self.assertNotIn("يحيي القطان", names(wakee))

    def test_segment_that_reaches_prophet_is_complete(self):
        _, p = parsed("muslim-7235")
        self.assertEqual(len(p["routes"]), 2)
        self.assertEqual(p["routes"][0]["join"], "complete_segment")
        self.assertEqual(p["fragments"], [])

    def test_new_wahaddathana_without_ha_is_new_route(self):
        # "... حدثنا خالد بن يزيد بن أبي مالك وحدثنا أبو حاتم حدثنا هشام بن خالد ..."
        _, p = parsed("ibnmajah-2449")
        self.assertEqual([names(r)[0] for r in p["routes"]], ["عبيد الله بن عبد الكريم", "ابو حاتم"])

    def test_taliq_is_fragment_not_route(self):
        # Bukhari: "... وقال الليث حدثني يونس عن ابن شهاب"
        _, p = parsed("bukhari-2494")
        self.assertEqual(len(p["routes"]), 1)
        self.assertEqual(names(p["routes"][0])[0], "عبد العزيز بن عبد الله العامري الاويسي")
        self.assertEqual([n["name"] for n in p["fragments"][0]][0], "الليث")

    def test_compiler_introduces_his_chain(self):
        # "قال أبو داود كتب إلي حسين بن حريث المروزي ..."
        _, p = parsed("abudawud-1915")
        self.assertEqual(names(p["routes"][0])[0], "حسين بن حريث المروزي")

    def test_compiler_remarks_after_prophet_are_ignored(self):
        _, p = parsed("tirmidhi-84")
        self.assertEqual(names(p["routes"][0])[-1], "بسره")


class Relatives(unittest.TestCase):
    def test_father_from_name_keeps_compound(self):
        # "عون بن عبد الله عن أبيه أو عن أخيه": father is "عبد الله", not "عبد"
        _, p = parsed("ibnmajah-3863")
        fathers = {r["names"][4]["name"] for r in p["routes"]}
        self.assertIn("عبد الله", fathers)
        self.assertIn("أخو عون بن عبد الله", fathers)

    def test_ibn_x_father_is_not_inferred(self):
        # "ابن نمير حدثنا أبي": the father of "ابن نمير" is not in the text
        _, p = parsed("muslim-7035")
        second = {r["names"][1]["name"] for r in p["routes"] if names(r)[0] == "ابن نمير"}
        self.assertIn("والد ابن نمير", second)

    def test_ubayy_is_resolved_from_name(self):
        # "الطفيل بن أبي بن كعب عن أبيه"
        _, p = parsed("tirmidhi-2547")
        self.assertEqual(names(p["routes"][0])[-1], "ابي بن كعب")


class Canonical(unittest.TestCase):
    def test_kunya_case(self):
        self.assertEqual(canonical("ابي هريره"), "ابو هريره")
        self.assertEqual(canonical("ابا هريره"), "ابو هريره")

    def test_ubayy_is_not_a_kunya(self):
        self.assertEqual(canonical("ابي بن كعب"), "ابي بن كعب")

    def test_ibn_inside_name(self):
        self.assertEqual(canonical("عبد الله ابن عمر"), "عبد الله بن عمر")


if __name__ == "__main__":
    unittest.main()
