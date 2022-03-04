import React from "react"
import {useStyles} from "./style"
import {Result} from "../../../stores/search/models"
import {Map, Marker, Popup, TileLayer} from "react-leaflet"

export interface ResultMapProps {
  results: Result[]
}

export function ResultMap(props: ResultMapProps) {
  const { results } = props
  const classes = useStyles()
  const position = [52.520008, 13.404954]
  return (
    <Map
      className={classes.map}
      center={position}
      zoom={13}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution="&copy; <a href=&quot;http://osm.org/copyright&quot;>OpenStreetMap</a> contributors"
      />
      {results && results.map((result, index) => (
        result.props.lat && result.props.lon && (
          <Marker key={index} position={[result.props.lat, result.props.lon]}>
            <Popup>A pretty CSS3 popup.<br />Easily customizable.</Popup>
          </Marker>
        )
      ))}
    </Map>
  )
}
