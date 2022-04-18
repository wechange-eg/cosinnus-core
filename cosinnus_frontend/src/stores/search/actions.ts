import {
  ReduxActionCreator,
  ReduxErrorActionCreator,
} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {Result} from "./models"

export const setFetchSearchResultsSuccess: ReduxActionCreator<Result[]> = (participants) => ({
  type: ActionType.FETCH_SEARCH_RESULTS_SUCCESS,
  payload: participants
})

export const setFetchSearchResultsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_SEARCH_RESULTS_ERROR,
  payload: Error(errorMessage),
  error: true
})
