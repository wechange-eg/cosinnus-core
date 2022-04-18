export interface ResultJson {
  id: string
  slug: string
  title: string
  description: string
  type: string
  lat: number
  lon: number
  address: string
  url: string
  iconImageUrl: string
  backgroundImageSmallUrl: string
  backgroundImageLargeUrl: string
  relevance: number
  topics: string[]
  sdgs: string[]
  portal: number
  group_slug: string
  group_name: string
  participant_count: number
  member_count: number
  content_count: number
  liked: boolean
}

export interface ResultProps {
  id: string
  slug: string
  title: string
  description: string
  type: string
  lat: number
  lon: number
  address: string
  url: string
  iconImageUrl: string
  backgroundImageSmallUrl: string
  backgroundImageLargeUrl: string
  relevance: number
  topics: string[]
  sdgs: string[]
  portal: number
  groupSlug: string
  groupName: string
  participantCount: number
  memberCount: number
  contentCount: number
  liked: boolean
}

export class Result {
  props: ResultProps

  public constructor(props: ResultProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Result object
   */
  public static fromJson(json: ResultJson) : Result {
    const props: ResultProps = {
      id: json.id,
      slug: json.slug,
      title: json.title,
      description: json.description,
      type: json.type,
      lat: json.lat,
      lon: json.lon,
      address: json.address,
      url: json.url,
      iconImageUrl: json.iconImageUrl,
      backgroundImageSmallUrl: json.backgroundImageSmallUrl,
      backgroundImageLargeUrl: json.backgroundImageLargeUrl,
      relevance: json.relevance,
      topics: json.topics,
      sdgs: json.sdgs,
      portal: json.portal,
      groupSlug: json.group_slug,
      groupName: json.group_name,
      participantCount: json.participant_count,
      memberCount: json.member_count,
      contentCount: json.content_count,
      liked: json.liked,
    }

    return new Result(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {ResultJson} - object in JSON format
   */
  toJson() : ResultJson {
    const props = this.props
    return {
      id: props.id,
      slug: props.slug,
      title: props.title,
      description: props.description,
      type: props.type,
      lat: props.lat,
      lon: props.lon,
      address: props.address,
      url: props.url,
      iconImageUrl: props.iconImageUrl,
      backgroundImageSmallUrl: props.backgroundImageSmallUrl,
      backgroundImageLargeUrl: props.backgroundImageLargeUrl,
      relevance: props.relevance,
      topics: props.topics,
      sdgs: props.sdgs,
      portal: props.portal,
      group_slug: props.groupSlug,
      group_name: props.groupName,
      participant_count: props.participantCount,
      member_count: props.memberCount,
      content_count: props.contentCount,
      liked: props.liked,
    }
  }

  /**
   * Get internal url
   */
  getUrl() : string {
    return "./#/r/" + this.props.id
  }
}
