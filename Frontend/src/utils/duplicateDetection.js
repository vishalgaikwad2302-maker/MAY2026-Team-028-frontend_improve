// Plain-JS duplicate detection: compares GPS distance and text overlap
// against existing complaints. No AI/ML — just Haversine + Jaccard.
// Designed to translate directly to a `GET /complaints/nearby` FastAPI
// endpoint later (same inputs, same thresholds, just moved server-side).

const EARTH_RADIUS_M = 6371000;
const DISTANCE_THRESHOLD_M = 200; // complaints within ~200m are "nearby"
const STRONG_TEXT_MATCH = 0.6; // location/description text overlap ratio
const WEAK_TEXT_MATCH = 0.35; // used only when combined with other signal

const STOPWORDS = new Set([
  "the", "a", "an", "near", "of", "at", "in", "on", "for", "and", "to",
  "is", "was", "were", "it", "this", "that", "with", "by",
]);

const tokenize = (text) =>
  (text || "")
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, " ")
    .split(/\s+/)
    .filter((w) => w.length > 1 && !STOPWORDS.has(w));

// Jaccard similarity: size of overlap / size of union, 0..1
function textSimilarity(a, b) {
  const setA = new Set(tokenize(a));
  const setB = new Set(tokenize(b));
  if (!setA.size || !setB.size) return 0;
  let overlap = 0;
  for (const word of setA) if (setB.has(word)) overlap++;
  const union = new Set([...setA, ...setB]).size;
  return overlap / union;
}

// Great-circle distance between two {lat, lng} points, in meters
function distanceMeters(a, b) {
  if (!a || !b) return null;
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(b.lat - a.lat);
  const dLng = toRad(b.lng - a.lng);
  const lat1 = toRad(a.lat);
  const lat2 = toRad(b.lat);
  const h =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLng / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(h));
}

// Same heuristic as above, but for flagging an *existing* complaint against
// the rest of the list — used to show a "Possible Duplicate" tag on cards
// and to warn a supervisor before they assign a crew to one.
// Only flags Pending/In Progress complaints; a Resolved/Cancelled one is
// done, so there's nothing left to duplicate-check it against or for.
export function getDuplicateMatches(complaint, allComplaints) {
  if (complaint.status !== "Pending" && complaint.status !== "In Progress") return [];
  const others = allComplaints.filter((c) => c.id !== complaint.id);
  return findPossibleDuplicates(complaint, others);
}

// Returns existing complaints that look like they might describe the same
// issue as `draft`, ranked by confidence (closest/most-similar first).
// Only checks against complaints still in play (Pending / In Progress) —
// a Resolved or Cancelled case isn't a "duplicate" worth blocking on.
export function findPossibleDuplicates(draft, complaints) {
  const active = complaints.filter(
    (c) => c.status === "Pending" || c.status === "In Progress"
  );

  const matches = active
    .map((c) => {
      const dist = distanceMeters(draft.coords, c.coords);
      const locationScore = textSimilarity(draft.location, c.location);
      const descScore = textSimilarity(draft.description, c.description);

      const isNearby = dist !== null && dist <= DISTANCE_THRESHOLD_M;
      const isDuplicate =
        isNearby ||
        locationScore >= STRONG_TEXT_MATCH ||
        (locationScore >= WEAK_TEXT_MATCH && descScore >= WEAK_TEXT_MATCH);

      if (!isDuplicate) return null;

      return {
        complaint: c,
        distance: dist,
        locationScore,
        descScore,
        // rough confidence score for sorting, not shown to the user
        confidence: (isNearby ? 0.5 : 0) + locationScore * 0.3 + descScore * 0.2,
      };
    })
    .filter(Boolean)
    .sort((a, b) => b.confidence - a.confidence);

  return matches;
}