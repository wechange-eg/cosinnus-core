export interface OrganizationJson {
  name: string
  description: string
  topics: string[]
  location: string
  image_url: string
}

export interface OrganizationProps {
  name: string
  description: string
  topics: string[]
  location: string
  imageUrl: string
}

export class Organization {
  props: OrganizationProps

  public constructor(props: OrganizationProps) {
    this.props = props
  }

  /**
   * Convert JSON response data into an object
   *
   * @param json - response data in JSON format
   * @returns {User} - Organization object
   */
  public static fromJson(json: OrganizationJson) : Organization {
    const props: OrganizationProps = {
      name: json.name,
      description: json.description,
      topics: json.topics,
      location: json.location,
      imageUrl: json.image_url,
    }

    return new Organization(props)
  }

  /**
   * Convert an object into JSON
   *
   * @returns {OrganizationJson} - object in JSON format
   */
  toJson() : OrganizationJson {
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
