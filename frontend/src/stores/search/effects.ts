import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {Result, ResultJson} from "./models"
import {
  setFetchSearchResultsError,
  setFetchSearchResultsSuccess,
} from "./actions"

/**
 * Fetch search results
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchSearchResults: ReduxThunkActionCreator<[string], Promise<void>> = (term) => (
  dispatch: Dispatch) => {
  return fetch(`${process.env.API_URL}/../../map/search/?q=${term}`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: {results: ResultJson[]}) => {
        dispatch(setFetchSearchResultsSuccess(data.results.map(json => Result.fromJson(json))))
      })
    } else {
      dispatch(setFetchSearchResultsError("Failed to fetch events"))
    }
  })
}
