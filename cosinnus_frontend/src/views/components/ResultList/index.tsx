import React from "react"
import {FormattedMessage} from "react-intl"
import {Card, CardActionArea, CardContent, CardMedia, Grid, Tab, Tabs, Typography} from "@material-ui/core"
import clsx from "clsx"

import {useStyles} from "./style"
import {Result} from "../../../stores/search/models";

export interface ResultListProps {
  results: Result[]
}

export function ResultList(props: ResultListProps) {
  const { results } = props
  const classes = useStyles()

  function renderResultCard(result: Result) {
    return (
      <Card className={clsx({
        [classes.card]: true,
      })}>
        <CardActionArea
          classes={{
            root: classes.actionArea,
            focusHighlight: classes.focusHighlight
          }}
          onClick={() => {
            const url = result.getUrl()
            if (url) window.location.href = url
          }}
        >
          <CardContent>
            <Typography component="h3">{result.props.title}</Typography>
          </CardContent>
        </CardActionArea>
      </Card>
    )
  }

  return (
    <Grid container spacing={4}>
      {results && results.map((result, index) => (
        <Grid item key={index} sm={12}>
          {renderResultCard(result)}
        </Grid>
      ))}
    </Grid>
  )
}
