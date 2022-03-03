import { makeStyles } from '@material-ui/core/styles';

export const useStyles = makeStyles((theme) => ({
  formControl: {
    width: "20rem",
    float: "right",
    [theme.breakpoints.down('sm')]: {
      width: "100%",
    },
  },
  tableContainer: {
    width: "100%",
    overflowX: "scroll",
  },
  table: {
  }
}))
