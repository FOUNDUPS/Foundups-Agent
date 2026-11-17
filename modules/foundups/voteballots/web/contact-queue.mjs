export const QUEUE_SIZES = Object.freeze([1, 3, 5]);

const OFFICE_ID = /^[A-Z][0-9]{6}$/;
const OFFICE_PHONE = /^202[2-9][0-9]{6}$/;
const SOURCE_URLS = new Map([
  ['House', 'https://clerk.house.gov/xml/lists/MemberData.xml'],
  ['Senate', 'https://www.senate.gov/general/contact_information/senators_cfm.xml'],
]);

export function phoneHref(number) {
  return typeof number === 'string' && OFFICE_PHONE.test(number) ? `tel:+1${number}` : null;
}

export function parseContactRoster(data) {
  if (data?.schemaVersion !== 1 || !/^\d{4}-\d{2}-\d{2}$/.test(data.retrievedOn)
    || !Number.isInteger(data.congress) || !data.states || !Array.isArray(data.offices) || !data.offices.length
    || !Array.isArray(data.sources) || data.sources.length !== 2) {
    throw new Error('Unrecognized contact snapshot');
  }
  const sourceChambers = new Set();
  for (const source of data.sources) {
    if (!source || sourceChambers.has(source.chamber) || !SOURCE_URLS.has(source.chamber)
      || source.url !== SOURCE_URLS.get(source.chamber) || !/^[a-f0-9]{64}$/.test(source.sha256)
      || !Number.isInteger(source.sourceRows) || source.sourceRows < 1) {
      throw new Error('Invalid contact snapshot source');
    }
    sourceChambers.add(source.chamber);
  }
  const officeIds = new Set();
  for (const office of data.offices) {
    if (!office || typeof office.id !== 'string' || !OFFICE_ID.test(office.id)
      || officeIds.has(office.id) || !['House', 'Senate'].includes(office.chamber)
      || typeof office.state !== 'string' || !/^[A-Z]{2}$/.test(office.state)
      || typeof data.states[office.state] !== 'string' || !data.states[office.state]
      || typeof office.name !== 'string' || !office.name.trim()
      || typeof office.district !== 'string' || (office.phone !== null && !phoneHref(office.phone))) {
      throw new Error('Invalid contact snapshot row');
    }
    officeIds.add(office.id);
  }
  return data;
}

export function selectOffices(offices, state, chamber) {
  return offices.filter((office) => office.state === state && (!chamber || office.chamber === chamber));
}

export function appendOffice(queue, office, size) {
  if (!office || !phoneHref(office.phone) || !QUEUE_SIZES.includes(size)
    || queue.length >= size || queue.some((entry) => entry.id === office.id || entry.phone === office.phone)) {
    return queue;
  }
  return [...queue, office];
}
