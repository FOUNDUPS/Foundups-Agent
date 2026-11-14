// Approximate state suggestions from generalized Census rings. The margin
// covers the map generalization and device uncertainty. It is not a boundary
// determination and must always be confirmed by the visitor.
const METERS_PER_DEGREE = 110_000;
const MAP_MARGIN_METERS = 8_000;
const MAX_ACCURACY_METERS = 25_000;

function longitudeDelta(longitude, origin) {
  return (longitude - origin + 540) % 360 - 180;
}

function inspectRing(ring, longitude, latitude, margin) {
  const origin = ring[0][0];
  const x = longitudeDelta(longitude, origin);
  const lonScale = METERS_PER_DEGREE * Math.cos(latitude * Math.PI / 180);
  const marginSquared = margin ** 2;
  let inside = false;
  let nearEdge = false;
  let [previousLongitude, previousLatitude] = ring[0];

  for (const [nextLongitude, nextLatitude] of ring.slice(1)) {
    const ax = longitudeDelta(previousLongitude, origin) - x;
    const ay = previousLatitude - latitude;
    const bx = longitudeDelta(nextLongitude, origin) - x;
    const by = nextLatitude - latitude;
    if ((ay > 0) !== (by > 0) && ax - ay * (bx - ax) / (by - ay) > 0) {
      inside = !inside;
    }

    if (!nearEdge) {
      const startX = ax * lonScale;
      const startY = ay * METERS_PER_DEGREE;
      const dx = (bx - ax) * lonScale;
      const dy = (by - ay) * METERS_PER_DEGREE;
      const lengthSquared = dx ** 2 + dy ** 2;
      const fraction = lengthSquared ? -(startX * dx + startY * dy) / lengthSquared : 0;
      const nearest = Math.max(0, Math.min(1, fraction));
      nearEdge = (startX + nearest * dx) ** 2 + (startY + nearest * dy) ** 2 <= marginSquared;
    }

    previousLongitude = nextLongitude;
    previousLatitude = nextLatitude;
  }
  return { inside, nearEdge };
}

export function suggestState({ latitude, longitude, accuracy }, boundaries) {
  if (boundaries?.schemaVersion !== 1 || !boundaries.states
    || !Number.isFinite(latitude) || Math.abs(latitude) > 90
    || !Number.isFinite(longitude) || Math.abs(longitude) > 180
    || !Number.isFinite(accuracy) || accuracy < 0 || accuracy > MAX_ACCURACY_METERS) {
    return null;
  }

  let suggestion = null;
  for (const [state, rings] of Object.entries(boundaries.states)) {
    for (const ring of rings) {
      const { inside, nearEdge } = inspectRing(ring, longitude, latitude, MAP_MARGIN_METERS + accuracy);
      if (!inside) continue;
      if (nearEdge || (suggestion && suggestion !== state)) return null;
      suggestion = state;
    }
  }
  return suggestion;
}
