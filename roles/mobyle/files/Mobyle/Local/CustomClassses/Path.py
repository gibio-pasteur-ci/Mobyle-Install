from Mobyle.Classes.DataType import DataType



class PathDataType( DataType ):
    
    def convert( self , value , acceptedMobyleType , detectedMobyleType = None , paramFile= False ):  
        """
        @param acceptedMobyleType: the MobyleType  accepted by this service parameter 
        @type acceptedMobyleType: L{MobyleType} instance
        @param detectedMobyleType: the MobyleType describing this data
        @type detectedMobyleType: L{MobyleType} instance
        """  
        return ( value , acceptedMobyleType )
    
    def detect( self , value ):
        mt = MobyleType( self )
        return mt  
    
    def validate( self, param ):
        if not param.ishidden():
            msg = "Path data type cannot be specify by users"
            raise UserValueError( parameter = param , msg = msg )
        else:
            return True
