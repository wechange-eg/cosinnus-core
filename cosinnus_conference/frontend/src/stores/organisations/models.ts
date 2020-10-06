export interface OrganisationJson {
  name: string
  description: string
  topics: string[]
  location: string
  image_url: string
}

export interface OrganisationProps {
  name: string
  description: string
  topics: string[]
  location: string
  imageUrl: string
}

export class Organisation {
  props: OrganisationProps

  public constructor(props: OrganisationProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Organisation object
   */
  public static fromJson(json: OrganisationJson) : Organisation {
    const props: OrganisationProps = {
      name: json.name,
      description: json.description,
      topics: json.topics,
      location: json.location,
      imageUrl: json.image_url,
    }

    return new Organisation(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {OrganisationJson} - object in JSON format
   */
  toJson() : OrganisationJson {
    const props = this.props
    return {
      name: props.name,
      description: props.description,
      topics: props.topics,
      location: props.location,
      image_url: props.imageUrl,
    }
  }
}
