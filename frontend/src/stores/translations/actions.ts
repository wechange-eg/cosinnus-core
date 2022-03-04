import {ReduxActionCreator, ReduxErrorActionCreator} from "../../utils/types"
import {ActionType} from "../../constants/actions"
import {TranslationsResponse} from "./effects"


export const setFetchTranslationsSuccess: ReduxActionCreator<TranslationsResponse> = translations => ({
  type: ActionType.FETCH_TRANSLATIONS_SUCCESS,
  payload: translations
})

export const setFetchTranslationsError: ReduxErrorActionCreator<string> = (
  errorMessage: string
) => ({
  type: ActionType.FETCH_TRANSLATIONS_ERROR,
  payload: Error(errorMessage),
  error: true
})

