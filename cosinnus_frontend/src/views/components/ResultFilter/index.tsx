import React from 'react';
import { Theme, createStyles, makeStyles } from '@material-ui/core/styles';
import clsx from 'clsx';
import Accordion from '@material-ui/core/Accordion';
import AccordionDetails from '@material-ui/core/AccordionDetails';
import AccordionSummary from '@material-ui/core/AccordionSummary';
import AccordionActions from '@material-ui/core/AccordionActions';
import Chip from '@material-ui/core/Chip';
import Button from '@material-ui/core/Button';
import Divider from '@material-ui/core/Divider';
import {useStyles} from "./style";
import InputBase from "@material-ui/core/InputBase";
import {RootState} from "../../../stores/rootReducer";
import {fetchSearchResults} from "../../../stores/search/effects";
import {connect as reduxConnect} from "react-redux";
import {withRouter} from "react-router";
import {DispatchedReduxThunkActionCreator} from "../../../utils/types";
import {faChevronDown} from "@fortawesome/free-solid-svg-icons";
import {FontAwesomeIcon} from "@fortawesome/react-fontawesome";
import {Typography} from "@material-ui/core";
import {FormattedMessage} from "react-intl";

interface ResultFilterProps {
  fetchSearchResults: DispatchedReduxThunkActionCreator<Promise<void>>
}

function mapStateToProps(state: RootState) {
  return {
  }
}

const mapDispatchToProps = {
  fetchSearchResults
}

export default function ResultFilterConnector(props: ResultFilterProps) {
  const classes = useStyles()

  return (
    <div className={classes.root}>
      <Accordion>
        <AccordionSummary
          expandIcon={<FontAwesomeIcon icon={faChevronDown} />}
          aria-controls="panel1c-content"
          id="panel1c-header"
        >
          <InputBase
            placeholder="Search…"
            classes={{
              root: classes.inputRoot,
              input: classes.inputInput,
            }}
            inputProps={{ 'aria-label': 'search' }}
            onKeyPress={onSearchKeyPress}
          />
        </AccordionSummary>
        <AccordionDetails className={classes.details}>
          <div>
            <Typography variant="h3"><FormattedMessage id="Topics" /></Typography>
            <Chip label="Topic 1" onDelete={() => {}} />&nbsp;
            <Chip label="Topic 2" onDelete={() => {}} />&nbsp;
            <Chip label="Topic 3" onDelete={() => {}} />
          </div>
        </AccordionDetails>
        <Divider />
        <AccordionActions>
          <Button size="small">Reset filters</Button>
          <Button size="small" color="primary">Apply filters</Button>
        </AccordionActions>
      </Accordion>
    </div>
  );
}

export const ResultFilter = reduxConnect(mapStateToProps, mapDispatchToProps)(
  withRouter(ResultFilterConnector)
)
