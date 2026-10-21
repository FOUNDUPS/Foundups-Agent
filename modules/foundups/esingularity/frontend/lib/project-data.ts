export type ClaimClass = 'A' | 'B' | 'C' | 'D';

export const projectData = {
  line: {
    url: 'https://line.me/ti/p/baXEozL_Q6',
    qrAsset: '/line-approved-qr.png',
  },
  event: {
    status: 'unconfirmed' as 'unconfirmed' | 'scheduled' | 'completed' | 'cancelled',
    startsAt: null as string | null,
    location: null as string | null,
    isPublic: null as boolean | null,
  },
  facility: {
    openedOn: '1994-04-06',
    publicFunctionEndedOn: '2021-06-24',
    originalConstructionCostJpy: 4_680_000_000,
    siteAreaSquareMetres: 33_717.36,
    floorAreaSquareMetres: 8_099.56,
    fiscal2018Users: 129_649,
    indexed2025ConstructionReferenceJpy: 6_799_000_000,
    indexedReferenceMethod: {
      originalIndex: 83.7,
      currentIndex: 121.6,
      originalYear: 1994,
      currentYear: 2025,
    },
    demolitionReferenceJpy: 1_580_000_000,
    demolitionReferenceStatus: 'council-question-material' as const,
  },
  onsenModel: {
    class: 'B' as ClaimClass,
    label: 'project-model-requires-validation' as const,
    greenfieldEquivalentJpy: { low: 1_280_000_000, high: 1_760_000_000 },
    brownfieldRecommissioningJpy: { low: 195_000_000, high: 270_000_000 },
    indicativeAvoidedCapexJpy: { low: 1_100_000_000, high: 1_500_000_000 },
  },
  sources: {
    masterProposalId: '1-wxF_I39svQH8AGvF2sryIk6ReAz2ctHe0-5-HypypM',
    landownerProposalId: '1WCqidzhU_9qyMxYCKj8UZ3lUv6qudCoWzy3qxClEznE',
    financialModelId: '1w00eZcfUMyaNu_wwQEf_GVNHpQamYScRdpB_QGecFJ0',
    fukuiPropertySheet: 'https://www.city.fukui.lg.jp/sisei/plan/reform/p071776_d/fil/SUKATTO.pdf',
    fukuiFacilityRecord: 'https://www.city.fukui.lg.jp/sisei/gikai/shigikaishikumi/p022677_d/fil/aramasi6.pdf',
    demolitionQuestionMaterial: 'https://www.city.fukui.lg.jp/sisei/gikai/shitsumon/p004052_d/fil/0806a.pdf',
    mlitDeflator: 'https://www.mlit.go.jp/statistics/details/t-other-2_tk_000362.html',
  },
} as const;

export type Locale = 'ja' | 'en' | 'pt';

export const locales: Locale[] = ['ja', 'en', 'pt'];
export const defaultLocale: Locale = 'ja';

export function isLocale(value: string): value is Locale {
  return locales.includes(value as Locale);
}

export function localeTag(locale: Locale) {
  if (locale === 'pt') return 'pt-BR';
  return locale;
}

export function formatInteger(value: number, locale: Locale) {
  return new Intl.NumberFormat(localeTag(locale), { maximumFractionDigits: 0 }).format(value);
}

export function formatDecimal(value: number, locale: Locale, digits = 2) {
  return new Intl.NumberFormat(localeTag(locale), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatJpyBillions(value: number, locale: Locale, digits = 2) {
  const billions = value / 1_000_000_000;
  if (locale === 'ja') return `${new Intl.NumberFormat('ja', { maximumFractionDigits: digits }).format(billions * 10)}億円`;
  return `¥${new Intl.NumberFormat(localeTag(locale), { maximumFractionDigits: digits }).format(billions)}B`;
}
