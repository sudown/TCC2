module Main where

minhaFuncao :: (Show a) => a -> IO String
minhaFuncao x = return ("Valor: " ++ show x)

main = minhaFuncao 10 >>= putStrLn
