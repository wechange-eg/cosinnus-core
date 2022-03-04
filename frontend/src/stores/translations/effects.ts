import {Dispatch} from "redux"

import {ReduxThunkActionCreator} from "../../utils/types"
import {setFetchTranslationsError, setFetchTranslationsSuccess} from "./actions"

export interface TranslationsResponse {
  locale: string
  catalog: {
    [x: string]: string
  }
}

/**
 * Fetch list of translations for current locale
 *
 * @returns {(dispatch: Dispatch) => Promise<void>} - return function
 */
export const fetchTranslations: ReduxThunkActionCreator<[string],
  Promise<void>> = () => (dispatch: Dispatch) =>
  fetch(`${process.env.API_URL}/jsi18n/`, {
    method: "GET"
  }).then(response => {
    if (response.status === 200) {
      response.json().then((data: TranslationsResponse) => {
        dispatch(setFetchTranslationsSuccess(data))
      })
    } else {
      dispatch(setFetchTranslationsError("Failed to fetch translations"))
    }
  })
