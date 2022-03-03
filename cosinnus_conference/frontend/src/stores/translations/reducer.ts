import { AnyAction } from "redux"

import { ActionType } from "../../constants/actions"

export interface TranslationsState {
  locale: string
  catalog: {
    [s: string]: string
  }
}

export function TranslationsReducer(
  state: TranslationsState = null,
  action: AnyAction
): TranslationsState {
  switch (action.type) {
    case ActionType.FETCH_TRANSLATIONS_SUCCESS: {
      return action.payload
    }
    case ActionType.FETCH_TRANSLATIONS_ERROR: {
      return state
    }
    default: {
      return state
    }
  }
}
